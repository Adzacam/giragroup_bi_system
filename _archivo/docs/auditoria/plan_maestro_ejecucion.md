# Plan de Ejecución Maestro — GiraGroup BI System

- **Fecha:** 2026-11-01 · **Rama:** `feature/sprint4-api-rbac`
- **Complementa:** [production_readiness_2026-11-01.md](production_readiness_2026-11-01.md) (25 hallazgos de la primera pasada).
- **Evidencia:** mediciones sobre la pila Docker en marcha. Las pruebas ejecutables están en [`tests/readiness/test_production_readiness.py`](../../tests/readiness/test_production_readiness.py) y [`tests/load/locust_readiness.py`](../../tests/load/locust_readiness.py).

## 0. Correcciones a la arquitectura declarada

El encargo describe componentes que no coinciden con el repositorio. Los agentes deben partir del estado real:

| Declarado | Real (`docker-compose.yml`) | Acción |
|---|---|---|
| Microservicio Analytics `:8003` | **No existe.** Forecast y KPIs viven en el monolito `api:8000`. | Quitar de la documentación o crearlo como `forecast-worker` (Fase 2). |
| Microservicio Storage `:8005` | **No existe.** Los archivos van a los volúmenes `./uploads` y `./output`. | Quitar de la documentación. |
| `giragroup_db` en `:5432` | Contenedor `:5432`, publicado en el host como **`127.0.0.1:5434`**. | Documentar 5434 en el host; no cambiar el puerto (los scripts locales ya lo usan). |
| `giragroup_catalog_db` en `:5433` | `127.0.0.1:5433` ✔ | — |
| PWA | No existía (sin manifest ni service worker). | **Implementada en esta pasada** (ver Fase 3). |
| 7 tablas de hechos | 7 ✔ (`fact_rendimiento_academico`, `fact_situacion_financiera`, `fact_cobranzas_proyectadas`, `fact_evaluacion_docente`, `fact_marketing`, `fact_rentabilidad`, `fact_forecast`) | — |

## 1. Resultados medidos frente a los umbrales

| Umbral | Medición | Estado |
|---|---|---|
| CMI `/kpis/cmi-completo`, 50 concurrentes, p95 < 3 s | Locust 30 s: **p95 58 ms**, 1431 req, 0 % errores | ✅ |
| `/forecast/analitica-macro`, p95 < 3 s | 1 petición en frío: 7,3 s. **50 concurrentes: p50 115 s**, timeouts a 120 s | ❌ Crítico |
| Inferencia BETO < 20 ms/oración | Antes: **1 036 ms/oración**. Corregido (2026-11-01): `/infer-batch` en GPU **8,0 ms/oración**; `/indice` 6,9 ms; `/infer` suelto 57 ms. Solo CPU (8 hilos): 31,6 ms/oración en lote, 101 ms suelto | ✅ con `docker-compose.gpu.yml` · ⚠️ solo CPU |
| Confianza media BETO ≥ 0,92 | Sobre las 180 frases gold reales: **0,987** (`/infer-batch`). El 0,847 inicial venía de frases sintéticas | ✅ |
| Bloqueo HITL exclusivo | Antes: **`[200, 200]`**. Corregido: UPDATE condicional atómico; 6 corridas seguidas con un solo ganador | ✅ |
| Cobertura de datos reales 100 % | 4 documentos `*_TEST` en el DW, `loadtest_user` y `qa_admin` activos como ADMIN, `fact_marketing` = 0 filas | ❌ |
| Timeouts Nginx (60/300/300 s) | Configurados así ✔. Con 300 s de lectura, un endpoint lento ocupa un worker hasta 5 min | ⚠️ |
| Conexiones PostgreSQL | `max_connections=100`; techo teórico de pools: api 4 workers × 15 + 3 servicios × 15 = **105** | ⚠️ |
| `reset_dw` conserva `users`, `dim_tiempo`, `cat_institucion` | Sí. Ninguna tabla fuera de la lista queda truncada por `CASCADE` (verificado en `pg_constraint`) | ✅ |

### 1.1 Diagnóstico de BETO (causa raíz medida con cProfile) — CORREGIDO

1. **Sobresuscripción de hilos:** PyTorch arranca con 24 hilos (núcleos del host WSL) dentro de un contenedor limitado. Un forward tarda 1 162 ms con 24 hilos y **53 ms con 4**.
2. **Dos forward por petición:** el pipeline NER (`ner_engine.extraer_entidades`) y luego otro forward para los embeddings de 768 dimensiones.
3. **Sin lotes:** cada oración es una petición HTTP y un forward.
4. **Validación:** `POST /infer` con `{"texto": …}` (campo mal nombrado) responde `status: success` con 0 entidades en lugar de 422.

Cambios aplicados:

- `ner_engine.configurar_hilos_torch()` fija `TORCH_NUM_THREADS` (4 por defecto, **8** en el compose) y un hilo inter-op; también lo usa `indice_confianza`.
- `BetoNEREngine.extraer_lote` hace ahora **un forward por bloque** (antes iteraba oración por oración); mismas entidades que la ruta suelta.
- Nuevo `POST /infer-batch` (hasta 256 oraciones). `POST /infer` exige `text` no vacío y responde **422** si falta (antes `success` vacío).
- `indice_confianza` usa CUDA si está disponible; índices CPU y GPU idénticos (diferencia máx. 0,00000; 0 de 180 bandas cambian).
- `docker-compose.gpu.yml` (override opcional): `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d pipeline`.
- **int8 descartado:** `BETO_INT8=1` existe como opción, pero baja el F1 de **0,973 a 0,920** (P 0,915 / R 0,925) sobre `data/test_gold_real.jsonl`. Desactivado por defecto.
- Pendiente: el segundo forward de `/infer` (embeddings de 768 para la vista de tensores) sigue aparte; solo afecta la ruta suelta interactiva.

### 1.2 Cascada FKResolver: especificación frente a implementación

| Estado | Especificación del encargo | Implementación (`backend/services/dw_loader.py`) | Veredicto |
|---|---|---|---|
| A | CI directo al DW | CI normalizado directo ✔. `"4567890 LP"` (CI + extensión departamental) se rechaza y cae a sintético | ⚠️ |
| B | `TEMP-SHA256` en `DimEstudiante` si confianza ≥ 0,85 | `TEMP-` + SHA-256[:12] ✔, pero también con confianza en **[0,60; 0,85)** y con confianza **`None`** | ❌ |
| C | `stg_entidad_no_resuelta` si confianza ∈ [0,60; 0,85) | Solo con confianza **< 0,60** (la banda media entra como hecho con `requiere_revision`) | ❌ diverge |
| — | — | `pipeline/normalization/fk_resolver.py` usa otro esquema: MD5[:8] (32 bits, homónimos colisionan) | ❌ |

Hay que decidir cuál es la regla oficial: la del encargo o la documentada en `pipeline/semantic/indice_confianza.py`. Las pruebas `xfail` de `TestCascadaConfianza` fijan la del encargo; si se adopta la otra, se cambian las pruebas y no el código.

### 1.3 HITL: carrera en el bloqueo — CORREGIDO

`lock_review_item` (`backend/routers/dataops.py:4289`) hace lectura → comprobación → escritura sin `SELECT … FOR UPDATE` ni versión. Corrección con una sola sentencia atómica:

```python
fila = db.execute(text("""
    UPDATE stg_entidad_no_resuelta
       SET lock_usuario_id = :uid, lock_expira = now() + interval '5 minutes'
     WHERE id_staging = :id
       AND (lock_usuario_id IS NULL OR lock_usuario_id = :uid OR lock_expira < now())
 RETURNING lock_expira"""), {"uid": current_user.id, "id": item_id}).first()
db.commit()
if fila is None:
    raise HTTPException(status_code=409, detail="El registro está siendo revisado por otro auditor.")
```

Aplicado en `lock_review_item` (con el ORM: `query(...).filter(..., or_(libre, propio, vencido)).update(...)`). Además, `resolve_review_item` toma la fila con `SELECT … FOR UPDATE` y responde **409** si el caso está bloqueado por otro auditor o ya fue resuelto (cubierto por `TestResolverRespetaBloqueo`). No se exige bloqueo previo porque el frontend todavía no llama a `/lock`: conectarlo al seleccionar un caso queda en la Fase 3.

Hallazgo nuevo (no corregido): `POST /review-tray/{id}/resolve` con un id inexistente responde **200**; debería ser 404.

---

## 2. Barrido rápido (QA / linter)

Formato pedido: `Archivo | Línea | Hallazgo | Corrección`. ✔ = corregido en esta pasada.

### 2.1 Datos demo / mock

| Archivo | Línea | Hallazgo | Corrección |
|---|---|---|---|
| `frontend/src/modules/admin/GestionUsuarios.jsx` | 11 | `FALLBACK_USERS` con 4 usuarios y correos reales como estado inicial | ✔ estado inicial `[]` |
| `frontend/src/modules/reports/CentroReportes.jsx` | 57 | `PROGRAMAS_DEFAULT` con programas inventados ("Maestría en Data Science", "Especialidad en Gestión Tributaria"…) y gestiones fijas hasta 2026 | ✔ programas del Catálogo Maestro; gestiones 2023 → año actual |
| `frontend/src/modules/finance/MetasGestion.jsx` | 53-54, 161 | Relleno `3800000`, `3480000`, `\|\| 18` | ✔ "—" y badge "Sin datos" |
| `frontend/src/modules/finance/ProyeccionFinanciera.jsx` | 194-212 | Literales `Bs. 3,800,000`, `1,510,800`, `97.4`, `79.2`, `2436`, `26.8` | ✔ valores del backend o "—" |
| `frontend/src/modules/academic/ProyeccionAlumnos.jsx` | 253, 262 | Relleno `5.75`, `MAPE 6.4` (el real es 92 %), `RMSE 135.1` | ✔ `?? '—'` |
| `frontend/src/modules/finance/RecaudacionCobranzas.jsx` | 34 | `?? 275000` | ✔ `?? 0` |
| `frontend/src/api/catalogApi.js` | 138 | Respaldo con `total_programas_activos: 18` cuando la API falla | ✔ `status: 'error'`, 0 programas |
| `frontend/src/context/AuthContext.jsx` | 13-17 | Migraba un rol `Demo User` guardado a **ADMIN** | ✔ eliminado |
| `frontend/src/modules/auth/LoginPage.jsx` + `constants/systemConstants.js:27` | 615 | Selector de cuentas demo con la contraseña `giragroup2026` en el bundle | ✔ solo con `import.meta.env.DEV` (verificado: el build ya no contiene la contraseña) |
| `frontend/src/modules/dataops/components/PipelineTelemetryDrawer.jsx` | 390-440 | Telemetría fabricada: "Confianza 98,4 % / 96,2 % / 94,7 %", `confidence: 96.5` fijo, SHA-256 completado con hex inventado hasta 64 caracteres, `?? 35` registros | Pendiente (Sonnet, Fase 1): mostrar solo lo que devuelve el backend |
| `backend/services/forecast_service.py` | 359, 445-500 | `resumen_cartera`, metas, ejecutado, Maestría inventada (ver informe 1) | Pendiente (Sonnet, Fase 1) |
| `pipeline/normalization/catalog_repository.py` | `PROGRAMAS_ACTIVOS_INSTITUCIONALES` | 18 programas con aranceles y punto de equilibrio en código | Pendiente: mover a `giragroup_catalog_db` |
| `frontend/src/modules/dataops/IngestView.jsx`, `PlainTextTransformationView.jsx` | 349, 220 | Origen por defecto `'GSHEETS_ACTA_NOTAS'` cuando el backend no lo detecta | Mostrar "No detectado" |
| `frontend/src/modules/dataops/components/BatchFlowHeader.jsx` | 7 | Rol por defecto `'AUDITOR_CALIDAD'` si no hay sesión | Usar `null` y ocultar las acciones |

**Universidades ajenas:** no hay referencias en datos ni vistas. Las coincidencias en `pipeline/semantic/formatter.py:86,298` y `pipeline/normalization/asymmetric_flattener.py:68` son el filtro que **elimina** "Unifranz/Bolivariana/BM Group": correcto, no tocar. Quedan nombres de fixtures en `backend/tests_root/sprint2/test_ingesta.py:176,180`, `test_categorizacion_y_cierre.py:36` y `sprint3/test_asymmetric_flattener_and_summary.py:83` (Baja: renombrar los fixtures).

**Endpoints:** todas las llamadas usan rutas relativas `/api/...` mediante `api/client.js` (`baseURL: ''`) y el proxy de Vite o el gateway. No hay URLs `:8000`/`:800x` en `src/`. `VITE_API_URL` no existe: el proyecto usa `VITE_API_TARGET` (en `vite.config.js`). ✔

**Tokens de color:** 33 archivos `.jsx` repiten hex literales (95 × `#D99B26`, 34 × `#0C1E33`, 28 × `#FAF9F6`). No aplicar `sed` a ciegas: Chart.js pinta en canvas y **no resuelve `var(--…)`**. Sustituir solo en props `style` / `className` y, para gráficos, leer el token con `getComputedStyle(document.documentElement).getPropertyValue('--color-gira-gold')`.

### 2.2 DevOps y persistencia

| Archivo | Hallazgo | Estado |
|---|---|---|
| `scripts/reset_dw.py:43`, `db/scripts/reset_dw.sql` | Preservan `users`, `dim_tiempo`, `cat_institucion`; ninguna FK arrastra tablas fuera de la lista | ✔ |
| `scripts/reset_dw.py` | Deja dimensiones derivadas de lotes de prueba (`dim_estudiante` con 41 `TEMP-…`, `dim_modulo`, `dim_docente`) | Añadir purga opcional `--incluir-dimensiones` |
| `backend/scripts/run_migrations.py` | Sin `DROP`/`TRUNCATE` sobre tablas preservadas ✔. Las migraciones se ejecutan también al arrancar la API (`main.py`) | Mover a un job |
| `docker-compose.yml` | `catalog_db` en 5433 ✔; `db` en **5434** en el host, no 5432 | Documentar |

### 2.3 Numeración de tareas

Encontrados fuera del rango GIRA-01…GIRA-39 / EP01…EP06: **GIRA-40, 41, 42, 43, 50, 52, 53, 54, 55, 56, 57, 58** (67 ocurrencias en 24 archivos): `backend/routers/forecast.py`, `backend/services/forecast_service.py`, `pipeline/analytics/*.py`, `pipeline/normalization/{fk_resolver,quality_rules,semantic_matcher}.py`, `pipeline/semantic/{formatter,ner_schema}.py`, `pipeline/ejecutar_sprint3.py`, `db/migrations/V004__add_forecasting_tables.sql` y las pruebas espejo en `tests/` y `backend/tests_root/` (incluido el nombre de archivo `test_formatter_gira40.py`).

La equivalencia vieja → nueva no está en el repositorio y no se puede inventar. Script de reemplazo, una vez que exista `docs/auditoria/mapa_gira.csv` (columnas `viejo,nuevo`, p. ej. `GIRA-54,GIRA-31`):

```bash
python -I - <<'EOF'
import csv, re, subprocess, pathlib
mapa = dict(csv.reader(open("docs/auditoria/mapa_gira.csv", encoding="utf-8")))
patron = re.compile(r"\b(" + "|".join(map(re.escape, sorted(mapa, key=len, reverse=True))) + r")\b")
archivos = subprocess.run(["git", "ls-files", "*.py", "*.sql", "*.js", "*.jsx", "*.sh"],
                          capture_output=True, text=True).stdout.split()
for ruta in map(pathlib.Path, archivos):
    texto = ruta.read_text(encoding="utf-8")
    nuevo = patron.sub(lambda m: mapa[m.group(1)], texto)
    if nuevo != texto:
        ruta.write_text(nuevo, encoding="utf-8")
        print("actualizado", ruta)
EOF
git mv tests/sprint3/test_formatter_gira40.py tests/sprint3/test_formatter_<nuevo>.py
```

---

## 3. Plan maestro en tres fases

**Reparto:** el **Agente Ejecutor (Sonnet)** hace los cambios que requieren criterio (lógica de negocio, concurrencia, modelos, diseño de componentes) y los cubre con pruebas. El **Agente de Barrido (Haiku)** hace tareas mecánicas, verificables con `grep`/SQL y sin decisiones de diseño: inventarios, sustituciones con mapa dado, comprobaciones de umbral y re-ejecución de suites. Ningún agente toca archivos asignados a otro en la misma fase.

### Fase 1 — Depuración y datos limpios

| # | Tarea | Agente | Archivos | Criterio de salida |
|---|---|---|---|---|
| 1.1 | Respaldo `pg_dump` de ambas BD antes de purgar | Haiku | — | `.dump` restaurable en una BD temporal |
| 1.2 | Desactivar `loadtest_user`/`qa_admin`; purgar documentos `*_TEST` y sus hechos | Haiku (SQL del informe 1, §3.1-6) | — | `TestHigieneDatos` en verde |
| 1.3 | Quitar los datos literales de `forecast_service` y leerlos de `fact_rentabilidad`, `fact_marketing` y `dim_meta` | Sonnet | `backend/services/forecast_service.py` | 0 literales numéricos de negocio; "sin datos" ⇒ `null` |
| 1.4 | Telemetría real en `PipelineTelemetryDrawer` | Sonnet | `PipelineTelemetryDrawer.jsx` | Sin porcentajes ni hashes fabricados |
| 1.5 | Mover `PROGRAMAS_ACTIVOS_INSTITUCIONALES` al catálogo 3NF | Sonnet | `catalog_repository.py`, `db/schema_catalogos.sql` | El resumen sale de SQL |
| 1.6 | Sacar la PII versionada (`output/lote1387_archivos/`, `email_previews`) + `gitleaks` | Haiku (inventario) → usuario (`git filter-repo` y force-push) | `.gitignore` | `gitleaks detect` limpio |
| 1.7 | Renumeración GIRA con `mapa_gira.csv` | Haiku (requiere el mapa del usuario) | 24 archivos | 0 coincidencias fuera de rango |
| 1.8 | Cargar `fact_marketing` desde el lote de inscripciones y retirar el respaldo silencioso a Excel | Sonnet | `dw_loader.py`, `time_series_extractor.py` | `fact_marketing` > 0; respuesta con `origen` explícito |

**Umbral de fase:** cobertura de datos reales **100 %** (0 documentos/usuarios de prueba, 0 literales de negocio en vistas y servicios), `pytest -m readiness_live -k Higiene` en verde.

### Fase 2 — Rendimiento backend, DataOps y fiabilidad algorítmica

| # | Tarea | Agente | Archivos | Criterio de salida |
|---|---|---|---|---|
| 2.1 | BETO: hilos, lote real, `/infer-batch`, 422 por campo inválido, GPU opcional | Sonnet | `pipeline/semantic/ner_engine.py`, `inference_server.py`, `indice_confianza.py`, compose | ✔ 8,0 ms/oración en GPU; F1 0,973 sin cambios |
| 2.2 | Confianza BETO ≥ 0,92 | — | — | ✔ 0,987 sobre frases gold (no requiere recalibración) |
| 2.3 | Bloqueo HITL atómico + `resolve` respeta bloqueo ajeno | Sonnet | `backend/routers/dataops.py` | ✔ prueba en vivo y unitarias en verde |
| 2.3b | El frontend toma el bloqueo al seleccionar un caso y lo libera al salir; `resolve` de id inexistente → 404 | Sonnet | `HumanReviewFlowView.jsx`, `dataops.py` | Pendiente |
| 2.4 | Cascada FKResolver según la regla oficial; CI con extensión; sustituir MD5[:8] | Sonnet | `dw_loader.py`, `fk_resolver.py` | Quitar `xfail` de `TestCascadaConfianza` y que pase |
| 2.5 | `forecast-worker`: precálculo a `fact_forecast`; los GET solo leen | Sonnet | `forecast_service.py`, `forecast_loader.py`, compose | `analitica-macro` p95 < 3 s con 50 concurrentes |
| 2.6 | Holt-Winters: `statsmodels`, selección add/mul por AIC + validación móvil, bandas que crecen con h, huecos ≠ 0, CAGR geométrico | Sonnet | `forecasting_holtwinters.py`, `forecasting_ols.py`, `time_series_extractor.py` | Quitar los `xfail` de `TestHoltWinters` / `TestOLSAnual` y que pasen |
| 2.7 | Pools (`pool_size=5, max_overflow=5`) o PgBouncer; `proxy_read_timeout` de 30 s en `/api/v1/kpis` | Haiku (valores dados) | `core/database.py` ×4, `gateway/nginx.conf` | Techo de conexiones < 80 |
| 2.8 | Correr Locust (3 escenarios) y la suite de readiness; volcar los resultados en `docs/evidencias/` | Haiku | — | `locust` con código de salida 0 |

**Umbrales de fase:** endpoints de tablero p95 **< 3 s** con 50 concurrentes; BETO **< 20 ms/oración** y confianza **≥ 0,92**; tasa de error < 1 %; 0 `xfail` restantes en `tests/readiness`.

### Fase 3 — Frontend PWA, UX/UI y responsividad

| # | Tarea | Agente | Estado |
|---|---|---|---|
| 3.1 | `manifest.webmanifest`, `sw.js` (Cache-First para estáticos, Network-First para la lista blanca de GET de tableros), registro solo en producción, limpieza de la caché de API al cerrar sesión | Sonnet | ✔ hecho y verificado (SW `activated`, manifest con 5 íconos) |
| 3.2 | Canvas: además de la pausa con pestaña oculta (ya existía), cuadro estático con `prefers-reduced-motion`, `Save-Data` o batería ≤ 20 % sin cargar | Sonnet | ✔ hecho |
| 3.3 | `MobileBottomNav`: mínimo 44 × 44 px, zona segura (`env(safe-area-inset-*)`, `viewport-fit=cover`), etiqueta de 11 px | Sonnet | ✔ medido: 6 accesos de 59 × 45 px a 375 px de ancho |
| 3.4 | Bandeja HITL: atajos A/E/J/K, aprobación diferida 10 s con "Deshacer", leyenda de atajos (oculta en táctil) | Sonnet | ✔ verificado: J/K navegan, E enfoca, A aprueba; "Deshacer" restaura el caso y no se envía ningún POST |
| 3.5 | Consolidar exportaciones en un `SplitButton`: `RendimientoAlertas.jsx:416` (menú Excel/PDF) + `:1383` (CSV suelto) → un menú; `PipelineTelemetryDrawer.jsx:667, 686, 899` (tres descargas .md) → una | Sonnet | Pendiente |
| 3.6 | Dos barras de carga superpuestas: `App.jsx:295` (`top-navigation-loading-bar`) y `Navbar.jsx:38` (`navbar-top-loading-bar`) → dejar la de `App.jsx` | Haiku | Pendiente |
| 3.7 | Skeletons: solo `CatalogosMaestros` y `MetasGestion` los tienen; añadirlos a CMI, Cartera, Recaudación, Proyecciones y Bandeja HITL | Sonnet | Pendiente |
| 3.8 | Hex literales → tokens (solo `style`/`className`; Chart.js con `getComputedStyle`) | Haiku con la regla dada | Pendiente |
| 3.9 | Selector "Institución": no hay ninguno visible; `IngestView.jsx:33` y `BatchFlowLayout.jsx:86` fijan "GiraGroup Posgrado" internamente | — | ✔ nada que retirar |

**Umbrales de fase:** Lighthouse PWA instalable; objetivos táctiles ≥ 44 px en ≤ 960 px; 0 cifras de relleno en vistas; LCP < 2,5 s en el build de producción.

---

## 4. Cómo correr las puertas

```bash
python -m pytest tests/readiness -q
```

```bash
docker exec giragroup_api python -c "from core.security import create_access_token;print(create_access_token({'sub':'1'}))"
```

```bash
READINESS_TOKEN=<jwt admin> READINESS_TOKEN_2=<jwt auditor> READINESS_DB_URL=postgresql://giragroup_user:<clave>@localhost:5434/giragroup_db python -m pytest tests/readiness -m readiness_live -q
```

```bash
LOCUST_TOKEN=<jwt> locust -f tests/load/locust_readiness.py --host http://localhost --users 50 --spawn-rate 10 --run-time 2m --headless CMIUser
```

BETO no se publica al host; sus puertas se corren desde la red Docker:

```bash
docker run --rm --network giragroup_bi_system_default -v "$(pwd -W):/repo" -w /repo -e READINESS_BETO_URL=http://pipeline:8006 -e PYTHONPATH=/repo:/repo/backend giragroup_bi_system-api sh -c "pip install -q pytest && python -m pytest tests/readiness -m readiness_live -k BETO -q"
```

Estado tras las correcciones de BETO y HITL: unitarias **20 aprobadas, 8 `xfail`**; en vivo **4 aprobadas, 1 `xfail`, 3 fallidas** (solo higiene de datos: documentos TEST, usuarios técnicos activos, `fact_marketing` vacío); BETO **3/3** con GPU. En `backend/tests_root/sprint4/test_rbac_enforcement.py` fallan 5 pruebas que ya fallaban antes de estos cambios (rutas `/pipeline/process` que devuelven 404).
