# Production Readiness Review — GiraGroup BI System

- **Fecha:** 2026-11-01 · **Rama:** `feature/sprint4-api-rbac` (commit `64a6450`)
- **Alcance:** monolito FastAPI (`backend/`), microservicios (`services/`), pipeline analítico (`pipeline/analytics/`), gateway nginx, `docker-compose.yml`, DW PostgreSQL en ejecución (`giragroup_db`).
- **Método:** revisión estática de código + consultas de solo lectura al DW vivo + ejecución cronometrada de `obtener_analitica_macro_completa()` dentro del contenedor `giragroup_api`.

> **Nota de alcance.** El dominio es BI académico-financiero (inscripciones, cartera, metas de recaudación, rendimiento). Los KPI de retail del encargo (DOH, venta perdida por quiebre, OTIF, Lead Time P85, GMROI, Strike Rate) **no existen en el sistema**; se auditaron sus equivalentes reales: cumplimiento de metas (mensual/anual), estado de cartera/mora, tasa de conversión de admisiones (≈ Strike Rate), ticket promedio, tasa de aprobación y el pronóstico Holt-Winters de inscritos/ingresos.

**Veredicto: NO apto para producción.** 6 hallazgos críticos (PII real versionada, bypass de MFA, datos fabricados en tableros, motor de pronóstico sin optimizar, credenciales compartidas, sin respaldos).

---

## 1. Matriz de hallazgos y vulnerabilidades

| # | Componente / Módulo | Pilar | Severidad | Diagnóstico técnico | Impacto en producción |
|---|---|---|---|---|---|
| 1 | `output/lote1387_archivos/ARCA_lote1387_860_filas.xlsx` (versionado en git) | 2 · Higiene / 4 · Secretos | **Crítica** | Contiene columnas `CÉDULA DE IDENTIDAD`, `APELLIDO PATERNO/MATERNO`, `NOMBRES` de 860 filas: PII real de estudiantes en el historial git. `uploads/test/BD_Cobranzas_giraGroup.xlsx` no lleva sufijo TEST y debe verificarse. | Exposición de datos personales a cualquiera con acceso al repo; borrar el archivo no lo elimina del historial. |
| 2 | `backend/main.py` `POST /api/v1/auth/login` + `docker-compose.yml` `api.ports: "8000:8000"` | 4 · Seguridad | **Crítica** | El monolito expone un login que emite JWT **sin OTP** ni chequeo `is_active`, y el puerto 8000 se publica en todas las interfaces (no `127.0.0.1`), saltándose el gateway que enruta `/api/v1/auth` al auth-service con MFA. | MFA eludible; usuarios desactivados obtienen token (luego fallan en `get_current_user`, pero el diseño es frágil). Sin rate limit → fuerza bruta. |
| 3 | `backend/services/forecast_service.py` `obtener_analitica_macro_completa()` / `obtener_matriz_viabilidad_programas()` | 2 · Higiene / 5 · KPI | **Crítica** | Valores literales servidos como datos: `resumen_cartera` (9150/3399/2504/143), `meta_catalogo` y `ejecutado_real` (17 meses), `mes_actual` "Mayo 2026", `meta_institucional_bs=15e6`, `recaudado_acumulado_2026=3.01e6`, históricos anuales 2023-2025 y una fila de **Maestría inventada** cuando no aparece en los datos. | El tablero predictivo muestra cifras que no salen del DW; hoy (nov-2026) el "mes actual" lleva 6 meses congelado. Decisiones sobre datos ficticios. |
| 4 | Contenedor `giragroup_api` / `backend/requirements.txt` | 6 · Holt-Winters | **Crítica** | `statsmodels` no está en requirements ni instalado ("statsmodels no está disponible" en log). Todas las corridas usan `_holt_winters_nativo` con α=0.2, β=0.1, γ=0.2 **fijos, no optimizados**; `aic=None`. La documentación afirma ajuste por MLE. | Pronósticos sin calibrar; los parámetros reportados no son estimados; la tesis describe un modelo distinto al que corre. |
| 5 | `backend/seed_users.py`, `DemoAccountsSelector.jsx`, tabla `users` | 2 · Higiene / 4 · Secretos | **Crítica** | 5 usuarios sembrados en cada arranque con la misma contraseña `giragroup2026` (también en el bundle del frontend). En BD viva existen `loadtest_user` y `qa_admin`, ambos **ADMIN activos**. Correos personales del autor como admin. | Cualquiera que lea el JS del login entra como ADMIN. |
| 6 | Infraestructura | 4 · Resiliencia | **Crítica** | No hay política de respaldo (`pg_dump`/WAL), ni script de restore, ni CI (`.github/` inexistente). Migraciones se ejecutan en el arranque de la API sin rollback. | Pérdida total del DW ante fallo de volumen; un despliegue roto no tiene vuelta atrás. |
| 7 | `services/auth-service/routers/auth.py:123,227` y `backend/output/email_previews/*.html` | 4 · Secretos | Alta | El OTP se escribe en el log en claro (`CÓDIGO OTP PARA …`) y el HTML del correo con el código se guarda en disco **y está versionado** (aparece modificado en `git status`). | Quien lea logs o el repo obtiene segundos factores válidos. |
| 8 | `.env.example`, `docker-compose.yml`, `core/database.py`, `core/security.py` | 4 · Secretos | Alta | `POSTGRES_PASSWORD: giragroup_secret_2026` en texto plano en compose; fallbacks en código con la misma contraseña y `SECRET_KEY="dev_secret_key_change_me_in_prod"`. Si falta `.env`, la API arranca con secreto JWT público. | Falsificación de JWT y acceso directo a BD si el entorno no se configura. Falla abierta en vez de cerrada. |
| 9 | `pipeline/analytics/time_series_extractor.py` `QUERIES` | 6 · HW / 5 · KPI | Alta | Ventana fija `fecha <= '2026-05-31'`: hoy faltan 5 meses. `META_MENSUAL_PROGRAMAS` usa `COALESCE(monto_ejecutado, monto_meta)` → mezcla metas como si fueran ventas reales; sin `GROUP BY` (periodos duplicados rompen `asfreq`). | Modelo entrenado con datos viejos y con *target leakage* (la meta entra como observación). |
| 10 | `fact_marketing` (0 filas) + fallback a Excel | 3 · Flujo E2E | Alta | El DW no tiene inscripciones; las series de alumnos se leen silenciosamente de `uploads/data/TBL_INSCRITOS.xlsx` en el hilo de la petición. La respuesta no indica el origen. | Ruptura del flujo ingesta→DW→pronóstico: el pronóstico no refleja lo cargado por DataOps. |
| 11 | `GET /api/v1/forecast/analitica-macro` | 1 · Rendimiento | Alta | Medido: **7,33 s** en frío. Lectura de Excel + 6 ajustes HW + OLS síncronos por request; nginx con `proxy_read_timeout 300s`. Caché por proceso (4 workers ⇒ 4 cachés). | Bajo carga los workers se bloquean; latencia p95 inaceptable para un tablero. |
| 12 | `pipeline/analytics/forecast_loader.py` | 3 · Crons | Alta | El batch de persistencia de pronósticos **no está programado** en ningún cron/servicio (solo lo invocan tests). `fact_forecast` tiene 0 filas. No existe ningún job programado en el sistema. | Todo se calcula on-demand; no hay reentrenamiento periódico ni registro de fallos. |
| 13 | `forecast_service.obtener_pronostico_alumnos()` | 3 · Flujo / 1 | Alta | (a) Lee `fact_forecast` con `ORDER BY periodo_mes LIMIT h` sin filtrar periodos futuros ni `generado_en` → sirve pronósticos caducados para siempre. (b) `except Exception: pass` oculta errores. (c) Un GET escribe en BD (`_persistir_en_fact_forecast`) con N+1 consultas por periodo. (d) `MAESTRIA` se mapea a `ALUMNOS_GLOBAL`. | Valores obsoletos sin aviso; filtro "Maestrías" muestra el total global. |
| 14 | `kpi_service.obtener_perspectivas_cmi_completo()` KPI 2 | 5 · KPI | Alta | Cumplimiento mensual toma el **último** `periodo_mes` (`order_by desc().first()`), normalmente un mes en curso o futuro con meta cargada y ejecutado parcial/nulo. | Cumplimiento sistemáticamente subestimado (puede mostrar 0 %). |
| 15 | `kpi_service` KPI 3 | 5 · KPI | Media | Cumplimiento anual = Σejecutado / Σmeta de la gestión completa (YTD vs meta anual) y sin filtro de gestión suma todos los años. | Porcentaje no comparable entre meses; sin filtro mezcla gestiones. |
| 16 | `kpi_service.obtener_kpis_financieros()` | 5 · KPI | Media | Campos `estudiantes_*` cuentan **filas** (`count(id_hecho_fin)`), mientras el CMI cuenta `distinct id_estudiante`. `fact_situacion_financiera` es una foto (181 `id_tiempo` distintos) sin filtro de fecha de corte: hoy hay 1 fila/estudiante, pero una segunda carga duplicará deuda y alumnos. "Previsionable" no existe en los datos (solo Vigente/En Mora). 126 de 229 filas tienen `monto_deuda = 0`. | Dos pantallas darán números distintos tras la próxima carga; deuda total inflada. |
| 17 | Filtros por programa (`ILIKE '%…%'`) en `kpi_service` y `time_series_extractor` | 1 · Consultas | Media | Segmentación por texto libre (`dm.programa ILIKE '%CURSO%'`) existiendo `cat_tipo_programa` en el catálogo. `'%CURSO%'` también casa con nombres que contienen "curso" en otro sentido; sin índice `pg_trgm`. EXPLAIN actual: seq scan de 571 filas (0,2 ms; irrelevante hoy, no escala). | Segmentos contaminados; con >100k filas el filtro será seq scan. |
| 18 | `routers/dataops.py:_serializar_archivos_lote` y `:2951-2959` | 1 · N+1 | Media | Consulta de staging por documento dentro de un bucle (N+1) y carga completa de `DimModulo/DimDocente/DimEstudiante` en memoria. | Degradación lineal con lotes grandes. |
| 19 | `routers/pipeline.py:process_pipeline` (`def`, 150 MB) | 1 · Asincronía | Media | Procesamiento de archivos de hasta 150 MB síncrono dentro del request; solo `dataops` usa `BackgroundTasks` (en proceso, sin reintentos ni persistencia de cola). | Un upload grande ocupa un worker hasta 300 s; si el worker muere el trabajo se pierde. |
| 20 | `docker-compose.yml` / Dockerfiles | 4 · Contenedores | Media | Bind mounts de código (`./backend:/app`) en todos los servicios, `web` corre `pnpm run dev` (Vite dev server) en vez de build estático, `api.Dockerfile` CMD con `--reload`, sin `healthcheck` en api/servicios, sin límites de recursos, imágenes sin pin de digest, `build-essential` en imagen final. | El contenedor no es inmutable: lo que corre depende del disco del host. |
| 21 | `gateway/nginx.conf` | 4 · Seguridad | Media | Sin `limit_req` (login, OTP, upload); sin TLS. | Fuerza bruta de OTP (6 dígitos) viable. |
| 22 | Observabilidad | 4 · Errores | Media | Sin middleware de telemetría/trazas ni métricas (no Sentry/Prometheus); manejadores `except Exception` que tragan errores en forecast, startup y extractor (circuit breaker de 30 s silencioso). | Fallos invisibles; la API "arranca igual" aunque las migraciones fallen. |
| 23 | `kpi_service` (`is_unit_test_mock`, `is_mock_scalar`) | 1 · Calidad | Baja | Ramas de código de producción que detectan mocks de pytest. | Comportamiento distinto en test y prod; los tests no prueban el código real. |
| 24 | `dim_origen_documental` | 2 · Higiene | Baja | 4 documentos `*_TEST.*` cargados en el DW vivo (ARCA, TBL_INSCRITOS, Google Forms, Moodle) y sus hechos derivados. Raíz del repo con `inscritos.csv`, `recaudacion.csv`, `confianza.csv`, `test.conll`, `backend/test_upload.py`, `sprint2_*_resultado.md`. | Hechos de prueba mezclados con productivos en KPIs. |
| 25 | `core/database.py` | 1 · Conexiones | Baja | `connect_timeout=1` s y pool por defecto (5+10) × 4 workers × 4 servicios. | Timeouts espurios bajo carga; agotamiento de conexiones a Postgres (max 100). |

---

## 2. Resultados de validación matemática

### 2.1 Holt-Winters (`pipeline/analytics/forecasting_holtwinters.py`)

| Aspecto | Estado | Detalle |
|---|---|---|
| α, β, γ | ❌ | Sin `statsmodels` se usan 0,2/0,1/0,2 fijos. Con `statsmodels`, `fit(optimized=True)` sí optimizaría por SSE. Reportar "parámetros estimados" es falso en el entorno actual. |
| Aditivo vs multiplicativo | ❌ | Fijo `trend="add", seasonal="add"`. No hay prueba de heterocedasticidad (p. ej. correlación entre nivel anual y amplitud estacional) ni comparación por AIC/holdout. Inscripciones con crecimiento CAGR ~27 %/año suelen tener amplitud estacional proporcional al nivel → multiplicativo o Box-Cox. Sin `damped_trend` pese a extrapolar tendencia. |
| Ciclos mínimos | ⚠️ | Mínimo 24 obs (2 ciclos) ✔. Serie real N=43 (3,6 ciclos) ✔. Pero el extractor acepta `len(df) >= 3` del DW y luego HW exige 24: incoherente. |
| Huecos | ❌ | `asfreq("MS").fillna(0.0)`: un mes sin datos se trata como **demanda cero**, y `ALUMNOS_GLOBAL` incluso elimina meses en cero con `HAVING SUM > 0` para luego reinsertarlos como 0. Un mes sin carga = colapso de demanda en el modelo. Debe interpolarse o marcarse como faltante. |
| Inicialización nativa | ⚠️ | `b0 = mean((y[m:2m]-y[:m])/m)` correcto; estacionalidad inicial con el primer ciclo solo (sensible a un primer año atípico). |
| Métrica de error | ❌ | RMSE **in-sample** (residuos sobre ajuste), sin holdout ni validación rodante (*time-series CV*). El "MAPE 92,01 %" que se publica en Caso 1 es el MAPE in-sample de la **recta OLS**, no de HW, y usa `max(y,1)` en el denominador (MAPE indefinido para y≈0 queda maquillado). No existe señal de rastreo (Tracking Signal). |
| Intervalo 95 % | ❌ | `ŷ ± 1,96·RMSE` constante para h=1…6. La varianza de HW crece con h: `Var(e_h) = σ²[1 + Σ_{j=1}^{h-1}(α + jαβ + γ·𝟙{j mod m = 0})²]`. La banda subestima la incertidumbre en h>1 y asume normalidad de residuos in-sample. |
| Campañas / estacionalidad concentrada | ❌ | Sin variables de intervención ni tratamiento de outliers. Un pico de campaña (p. ej. lanzamiento de diplomado) entra al componente estacional con γ fijo y se replica cada 12 meses; la caída post-campaña empuja el nivel hacia abajo. Recomendado: detectar outliers (residuo > 3σ), winsorizar antes de ajustar o modelar campaña como regresor (ETS → SARIMAX con dummy). |
| Leakage | ❌ | `META_MENSUAL_PROGRAMAS` = `COALESCE(ejecutado, meta)`: la meta se usa como observación cuando falta ejecutado. |
| Resultado medido | — | `ALUMNOS_GLOBAL`: N=43, RMSE=135,12 alumnos, MAPE(OLS)=92,01 %, latencia 7,33 s. Un MAPE de 92 % invalida la recta OLS como referencia visual. |

### 2.2 OLS anual (`forecasting_ols.py`)

- `cagr_historico_pct` es la **media aritmética de variaciones interanuales**, no un CAGR. CAGR correcto: `(V_fin/V_ini)^{1/(n-1)} − 1`. Con 8,04 M → 12,91 M Bs (2023→2025): CAGR = 26,7 %; la media aritmética da otro valor y sesga al alza con crecimiento irregular.
- El módulo declara "no se reporta IC con N=3", pero `forecast_service` publica `ic_lower/ic_upper = ±5 %` y "banda operativa". Contradicción metodológica: o se omite o se etiqueta como tolerancia de gestión, no como IC.

### 2.3 Otras fórmulas de `forecast_service`

- **CAGR global (Caso 1):** `(y_last / y_first)^{12/n} − 1` compara meses distintos (nov-2022 vs mes final): mezcla estacionalidad con crecimiento. Usar sumas de 12 meses móviles (LTM) en extremos.
- **Matriz de viabilidad:** `proy_6m = max(8, c25·0,5·(1+ajuste))` fuerza un piso de 8 inscritos (dato fabricado para programas en declive); `c26` es año parcial y se compara contra años completos; umbrales 35/18 y CAGR 5 %/−10 % sin fuente.

### 2.4 KPIs del CMI (`kpi_service.py`)

| KPI | Fórmula implementada | Fallo | Corrección |
|---|---|---|---|
| Cumplimiento mensual | `Σejec/Σmeta` del último `periodo_mes` | Toma mes en curso/futuro → subestima | Último mes **cerrado** con `monto_ejecutado IS NOT NULL`, o `periodo_mes < date_trunc('month', now())` |
| Cumplimiento anual | `Σejec/Σmeta` de toda la gestión | YTD vs meta anual completa | `Σejec_YTD / Σmeta_YTD` (mismos meses) y reportar aparte avance vs meta anual |
| Estado de cartera / mora % | `(mora+prev)/total` por `distinct id_estudiante` agrupado por estado | Sin fecha de corte: un alumno con 2 fotos cuenta en 2 estados y suma deuda 2 veces | Filtrar `id_tiempo = max(id_tiempo)` por estudiante (`DISTINCT ON`) |
| KPIs financieros básicos | `count(id_hecho_fin)` | Cuenta filas, no estudiantes | `count(distinct id_estudiante)` |
| Conversión admisiones (≈ Strike Rate) | `Σinscritos/Σleads` con `leads>0` | Correcto y protegido contra /0; `fact_marketing` vacío ⇒ `None` | Mostrar "sin datos" en UI, no 0 % |
| Ticket promedio | `recaudación/matrícula` | Correcto con guarda /0 | — |
| Tasa aprobación | `aprobados/evaluados` | Correcto (guarda /0) | — |
| División entre cero | — | Protegidas en kpi_service ✔; `forecast_service` usa `max(1, …)` que oculta casos degenerados | Devolver `None` |

---

## 3. Plan de remediación priorizado

### 3.1 Quick wins (≤ 1 día cada uno)

1. **Sacar PII del repositorio** (hallazgo 1)
   ```bash
   git rm --cached output/lote1387_archivos/ARCA_lote1387_860_filas.xlsx backend/output/email_previews/*.html services/auth-service/output/email_previews/*.html
   printf '\noutput/lote*/\n**/output/email_previews/\n' >> .gitignore
   ```
   Luego purgar historial (requiere coordinación y force-push; acción irreversible):
   ```bash
   git filter-repo --path output/lote1387_archivos --path-glob '*/email_previews/*' --invert-paths
   ```
2. **Cerrar el bypass de MFA** (hallazgo 2): en `docker-compose.yml` `api.ports` → `"127.0.0.1:8000:8000"` (o eliminar y usar solo `expose`); eliminar `swagger_oauth2_login` de `backend/main.py` o montarlo solo si `STANDALONE_MONOLITH=true`, añadiendo chequeo `user.is_active`.
3. **Instalar statsmodels** (hallazgo 4): `backend/requirements.txt` → `statsmodels==0.14.4`, `numpy` pinneado; reconstruir `api`. Si el fallback nativo se usa, devolver `"motor": "nativo_no_optimizado"` en la respuesta.
4. **Fallar cerrado en secretos** (hallazgo 8):
   ```python
   SECRET_KEY = os.environ["SECRET_KEY"]  # sin default
   ```
   y `DATABASE_URL` sin fallback; en compose usar `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}`. Rotar `giragroup_secret_2026` y el `SECRET_KEY` actual.
5. **Dejar de registrar OTP** (hallazgo 7): eliminar las líneas `auth.py:123,227` o condicionarlas a `APP_ENV=test`; desactivar el volcado de `email_previews` fuera de test.
6. **Purga de usuarios y datos de prueba** (hallazgos 5, 24) — ejecutar tras respaldo:
   ```sql
   BEGIN;
   UPDATE users SET is_active = false WHERE username IN ('loadtest_user','qa_admin');
   -- Hechos derivados de documentos de prueba (ajustar a las FK reales de cada hecho)
   DELETE FROM staging_registros_crudos WHERE id_documento IN
     (SELECT id_documento FROM dim_origen_documental WHERE nombre_archivo ILIKE '%\_TEST.%' ESCAPE '\');
   -- repetir DELETE para cada fact_* con columna id_documento / id_lote del lote de prueba
   DELETE FROM dim_origen_documental WHERE nombre_archivo ILIKE '%\_TEST.%' ESCAPE '\';
   COMMIT;
   ```
   Seed: leer contraseñas iniciales de variables de entorno, forzar cambio en primer login y no sembrar en `ENVIRONMENT=production`; eliminar `DemoAccountsSelector` del build de producción (`import.meta.env.DEV`).
7. **Corregir KPI mensual** (hallazgo 14):
   ```python
   q_rent_m = q_rent_m.filter(FactRentabilidad.monto_ejecutado.isnot(None),
                              DimTiempo.fecha < func.date_trunc('month', func.now()))
   ```
8. **Corregir ventana y leakage del extractor** (hallazgo 9): `dt.fecha <= date_trunc('month', now()) - interval '1 day'`; `META_MENSUAL_PROGRAMAS` → `SUM(fr.monto_ejecutado) … WHERE fr.monto_ejecutado IS NOT NULL GROUP BY dt.periodo_mes`.
9. **Respaldo diario** (hallazgo 6) — tarea programada del host:
   ```bash
   docker exec giragroup_db pg_dump -U giragroup_user -Fc giragroup_db > backups/giragroup_db_$(date +%F).dump
   ```
   y probar restauración: `pg_restore -c -d giragroup_db backups/<archivo>.dump` sobre una BD temporal.
10. **Rate limiting** (hallazgo 21) en `gateway/nginx.conf`:
    ```nginx
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
    location /api/v1/auth { limit_req zone=auth burst=5 nodelay; proxy_pass http://auth_service; }
    ```

### 3.2 Estructurales (1–3 sprints)

1. **Eliminar datos literales del tablero predictivo** (hallazgo 3): `resumen_cartera`, metas/ejecutado mensual, acumulados y meta institucional deben salir de `fact_rentabilidad`, `fact_marketing` y `dim_meta`. Borrar la fila de Maestría inventada y el piso `max(8, …)`. Si no hay datos, responder `null` y que la UI muestre "sin datos".
2. **Pipeline de pronóstico batch** (hallazgos 11, 12, 13): servicio `forecast-worker` (o cron del contenedor `pipeline`) que corra `forecast_loader` tras cada lote consolidado y mensualmente; persiste en `fact_forecast` con `generado_en`, `version_modelo`, `alpha/beta/gamma`, métricas de holdout. Los GET solo leen `fact_forecast WHERE generado_en = max AND periodo > último mes cerrado`; sin escrituras en GET. Objetivo p95 < 300 ms.
3. **Recalibración de Holt-Winters:**
   - Selección automática entre `{add, mul} × {damped, no damped}` (+ Box-Cox) por AIC y por MAPE/RMSE en **validación rodante** (origen móvil, últimos 6 meses, h=1…6).
   - Intervalos por simulación (`model.simulate(nsimulations=h, repetitions=1000)`) o fórmula analítica que crece con h.
   - Huecos: interpolación/NaN, no 0; outliers de campaña: winsorizar o regresor de intervención.
   - Publicar MAPE (o sMAPE/MASE si hay ceros), RMSE out-of-sample y **Tracking Signal** `TS = Σ(e_t) / MAD`, alerta si |TS| > 4.
   - Sustituir el "CAGR" aritmético por CAGR geométrico y retirar las bandas ±5 % etiquetadas como IC.
4. **Flujo E2E DataOps → DW** (hallazgo 10): `fact_marketing` debe poblarse desde el lote de inscripciones; eliminar el fallback silencioso a Excel en producción (o devolver `origen: "archivo_excel"` explícito).
5. **Modelo dimensional:** sustituir `ILIKE '%…%'` por FK a `cat_tipo_programa` en `dim_modulo` (`id_tipo_programa`); filtros por igualdad indexada. Snapshot financiero con `fecha_corte` y vista `v_cartera_actual` (`DISTINCT ON (id_estudiante) … ORDER BY id_tiempo DESC`) usada por todos los KPI de cartera.
6. **Cola de trabajos** (hallazgo 19): mover `process_pipeline` y la evaluación de lotes a un worker (RQ/Celery + Redis o tabla `job` con `SELECT … FOR UPDATE SKIP LOCKED`), con reintentos, timeout y estado consultable.
7. **Contenedores de producción** (hallazgo 20): `docker-compose.prod.yml` sin bind mounts de código, imagen multi-stage (sin `build-essential`), `web` servido como estático por nginx (`pnpm build`), `healthcheck` en api/servicios, `deploy.resources.limits`, imágenes con tag fijo; migraciones como job separado (`run_migrations.py`) con transacción y script de rollback, no en `startup`.
8. **Observabilidad** (hallazgo 22): logging JSON con `request_id`, middleware de métricas (`prometheus-fastapi-instrumentator`), Sentry o equivalente; reemplazar `except Exception: pass` por log + error explícito.
9. **CI** (`.github/workflows/ci.yml`): `pytest` (unificar `tests/` y `backend/tests_root/`, hoy duplicados), `pip-audit`, `gitleaks` (impide reintroducir PII/secretos), build de imágenes. Eliminar ramas `is_unit_test_mock` de `kpi_service` y testear contra Postgres real (testcontainers).
10. **Pool de conexiones** (hallazgo 25): `pool_size=5, max_overflow=5, connect_timeout=5`, y `pgbouncer` si se mantienen 4 workers × 4 servicios.

### 3.3 Orden sugerido

| Semana | Acciones |
|---|---|
| 0 (inmediato) | QW 1, 2, 4, 5, 6 (seguridad y PII) |
| 1 | QW 3, 7, 8, 9, 10 · Estructural 1 |
| 2–3 | Estructurales 2, 3, 4 |
| 4–6 | Estructurales 5–10 |
