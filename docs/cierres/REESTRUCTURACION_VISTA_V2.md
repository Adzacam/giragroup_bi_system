# REESTRUCTURACIÓN VISTA V2 — 2026-11-20

Objetivo (1 línea): rehacer el Cuadro de Mando Integral V2 (`/v2/dashboard`): quitar Power BI, mapa estratégico horizontal con card folders, vista general y desglose por perspectiva, analítica predictiva ordenada, botón Actualizar con Sileo y configuración editable por admin y analista. Todo con código limpio y sin archivos sobrantes.

Entrada: `CIERRE_FRONT_V2.md` (Ronda 4) y `CIERRE_F5V.md` leídos; rama base `beto-integracion` `38e317f`.
Inspección: código leído completo. La vista en vivo quedó detenida en el 2FA del login, así que la captura «antes» pasa al Loop 0.

**Método:** 10 loops. Cada loop se ejecuta en un chat 2 por separado y cierra con su `CIERRE_RV2_L<n>.md` antes de empezar el siguiente. Ningún loop cambia cifras del DW, del pronóstico ni de los 23 KPI.

---

## 1. Clasificación (qué va junto y qué no)

| Loop | Sección | Capa | Agente | Depende de | Puede ir en paralelo con | Riesgo |
|---|---|---|---|---|---|---|
| L0 | Línea base y capturas «antes» | Front + back (solo lectura) | `dev-baja` | — | — | Bajo |
| L1 | Retirar Power BI (tabla queda, D1-b; rol se borra, D2) | Front + back + migración 020 | `dev-media` | L0 | — | Medio |
| L2 | Refactor estructural del CMI (sin cambio visual) | Front | `dev-media` | L1 | — | Medio |
| L3 | Mapa estratégico horizontal + vista general del CMI | Front + endpoint nuevo | `dev-media` | L2 | L5, L6 | Medio |
| L4 | Desglose por perspectiva (KPI arriba, gráficas abajo, buscador) | Front + endpoint nuevo | `dev-media` | L3 | L5 | Medio |
| L5 | Analítica predictiva reorganizada | Front | `dev-media` | L2 | L3, L4, L6 | Medio |
| L6 | Botón Actualizar con animación + Sileo | Front | `dev-baja` | L2 | L3, L5 | Bajo |
| L7 | Configuración: roles, KPI y gráficas personalizadas (esquema `app`, D3) | Back + BD + front | `dev-alta` (diseño) → `dev-media` | L4 | — | Alto (control: invariantes 51 / 10 / 23 recalculados) |
| L8 | Limpieza de archivos y código muerto (`_archivo/` y `.agent*` se conservan, D5) | Repo | `dev-baja` | L1–L7 | — | Medio |
| L9 | Verificación final en navegador + cierre | Front + back | `dev-baja` | L8 | — | Bajo |

Orden recomendado: **L0 → L1 → L2 → (L3 ‖ L5 ‖ L6) → L4 → L7 → L8 → L9**.
L2 va antes del rediseño porque `CuadroMandoIntegral.jsx` tiene 1.206 líneas con estilos en línea. Así cada loop siguiente toca un archivo propio y los loops paralelos no chocan.

---

## 2. Loops

### L0 — Línea base y capturas «antes» (`dev-baja`)
| ID | Tarea | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|
| L0-1 | Correr `npx vitest run`, `npm run build` y `pytest` (suites sprint1, sprint5, f3v) | Conteos passed/failed/skipped anotados | `rv2_l0_pruebas.txt` |
| L0-2 | Capturar `/v2/dashboard` en los modos Perspectivas, Analítica predictiva, Configuración y Power BI, a 1440 px y 375 px, claro y oscuro (Lean ingresa el 2FA en el panel) | 16 capturas | `rv2_l0_capturas/` |
| L0-3 | Guardar el JSON de `GET /api/v1/cmi/scorecard` (todas las gestiones) y de `GET /forecast/analitica-macro?horizonte=6` | 2 JSON con sha256 | `rv2_l0_scorecard.json`, `rv2_l0_macro.json` |
| L0-4 | Inventario de candidatos a limpieza (`git ls-files`, tamaño, referencias con `grep`) | CSV: ruta · versionado · tamaño · referencias · propuesta | `rv2_l0_inventario_limpieza.csv` |

L0-3 sirve de oráculo: L3, L4 y L5 deben mostrar exactamente estas cifras.

### L1 — Retirar Power BI (`dev-media`) · requiere D1 y D2
| ID | Tarea | Criterio de aceptación |
|---|---|---|
| L1-1 Front | Borrar `modules/admin/cmi/CmiPowerBi.jsx` y `api/powerbiApi.js`. Quitar el modo D, `veePowerBi`, el import `MonitorDown`, `glosarioTextos.powerbi` y el bloque CSS «Acceso a Power BI Desktop» de `cmi.css` (línea 285). Reescribir los textos que nombran Power BI: subtítulo del `PageHeader`, intro de `CmiConfiguracion`, comentario de `cmiFormat.js` y frase de `LoginHeroPane.jsx:300`. Quitar el caso L3-R3 de `v2Ronda3.test.jsx` | `grep -rniE "powerbi\|power bi\|pbix" frontend/src` = 0 |
| L1-2 Back | Borrar `backend/routers/powerbi.py` y su `include_router` en `main.py` (líneas 38 y 187). Borrar `tests/sprint5/test_powerbi_retencion.py` y `backend/tests/test_powerbi_delete.py`. Reescribir los docstrings de `routers/cmi.py` y `routers/kpis.py`. `services/auth-service/schemas/kpi_schemas.py`: revisar y alinear | `GET /api/v1/powerbi/informe` → 404; pytest sin regresiones frente a L0 |
| L1-3 BD | Según D1: **(a)** migración nueva `020_retirar_powerbi.sql` (idempotente: `DROP TABLE IF EXISTS public.powerbi_informe_version`; rol `powerbi_reader` según D2), agregada a `MIGRACIONES_EN_ARRANQUE`, con `007` intacta en el historial y `test_migraciones_arranque.py` ajustado; **o (b)** dejar la tabla sin uso y documentarla | Conteo de tablas public+bi = valor decidido en D1 |
| L1-4 Archivos | Borrar `powerbi/` completo (`.pbix` y guía), `uploads/powerbi/` y `_archivo/powerbi/` (6 archivos, D5) | `git ls-files powerbi` = 0 |
| L1-5 No tocar | Los nombres de programa «PROGRAMA EXPERTO EN MICROSOFT POWER BI» en `db/seeds/seed_catalogos.sql` son **datos reales del catálogo** y se quedan. `scripts/generar_figura_3_2_arquitectura.py`, `3_3_despliegue` y otros generadores de figuras de la tesis tampoco se tocan (chat 4, según D1) | Diff sin cambios en `db/seeds/` ni `scripts/generar_figura*` |

Salida: `rv2_l1_grep_powerbi.txt` y `rv2_l1_pruebas.txt`.

### L2 — Refactor estructural del CMI, sin cambio visual (`dev-media`)
Partir `CuadroMandoIntegral.jsx` (1.206 líneas) en:
```
modules/admin/cmi/
  CmiPage.jsx              ← orquestador: modos y estado mínimo (< 150 líneas)
  CmiHeader.jsx            ← título, Actualizar, Configuración, Exportar
  CmiModeSwitch.jsx        ← selector de modo (pill segment)
  useExportarCmi.js        ← lógica de exportación
  scorecard/               ← CmiScorecard partido: IndiceGlobal, MapaEstrategico, TarjetaKpi, SeccionPerspectiva
  prediccion/              ← PrediccionPage + Caso1..Caso4 + DetallePrediccion + chartConfig.js
```
- Pasar los estilos en línea a clases de `cmi.css` con los tokens existentes (`--color-gira-gold`, `--color-gira-navy`, `--color-paper-white`, `--color-mist-gray`, `--cmi-ok/warn/bad`). Sin colores nuevos.
- Los colores de Chart.js salen de los tokens en un solo `chartTheme.js`, no repetidos en cada gráfica.
- La ruta V1 `/dashboard` sigue igual: los mismos componentes con la rama `isV2Active()`.

Criterios: (a) ningún archivo del CMI pasa de 300 líneas; (b) las capturas de L2 son iguales a las de L0 (comparación visual); (c) vitest y build en verde; (d) 0 imports sin uso (`eslint --rule no-unused-vars`). Salida: `rv2_l2_lineas.txt` (wc -l antes y después) y `rv2_l2_pruebas.txt`.

### L3 — Mapa estratégico horizontal + vista general del CMI (`dev-media`) · skill `/frontend-design` + `dataviz`
**Arriba (hero):**
- Fila 1: gestión (segment), leyenda del semáforo y buscador global de KPI.
- Fila 2: índice global compacto a la izquierda y **4 `CardFolderV2` de perspectiva en horizontal**, ordenadas por causa → efecto de izquierda a derecha: Aprendizaje → Procesos → Estudiantes y mercado → Financiera. Entre una y otra va un conector «→» animado. Cada folder muestra índice, banda de semáforo y «n de m evaluados».
- Responsivo: 4 columnas (≥ 1200 px) → 2×2 (≥ 640 px) → carrusel horizontal con `scroll-snap` (< 640 px).

**Abajo, sin perspectiva seleccionada: «Vista general»** (pensada para un analista):
1. **Matriz de semáforo de los 23 KPI** (heatmap perspectiva × KPI; clic abre `CmiDetalleKpi`).
2. **Índice por perspectiva frente a la gestión anterior** (barras agrupadas o bullet chart contra la meta 100).
3. **Alertas prioritarias:** KPI en rojo y ámbar ordenados por brecha a la meta, con tendencia.
4. **Evolución del índice global por gestión** (línea).
5. **Cobertura del CMI:** KPI evaluados, sin dato (con su motivo, `FALTANTES`) y sin umbral.

Backend: `GET /api/v1/cmi/resumen` lee `bi.vw_cmi_global` y `bi.vw_cmi_perspectiva` para todas las gestiones, con la misma VISIBILIDAD por rol y la misma caché de 60 s. Solo lectura, sin vistas nuevas.

Criterios: (a) mapa horizontal en 1440 px y carrusel en 375 px; (b) las cifras coinciden al 100 % con `rv2_l0_scorecard.json`; (c) test de API para `/cmi/resumen` (rol ADMIN ve 4 perspectivas, ANALISTA_FINANCIERO ve 1); (d) animación de entrada escalonada de 40–60 ms por folder, que respeta `prefers-reduced-motion`. Salida: `rv2_l3_cifras_vs_l0.json` y `rv2_l3_capturas/`.

### L4 — Desglose por perspectiva (`dev-media`) · skill `/data:build-dashboard` + `dataviz`
Al pulsar un folder, el panel se expande con `useContainerTransformV2` (la vista general se oculta y queda el botón «Volver a vista general»):
- **Arriba:** las cards de KPI de esa perspectiva con el diseño de la V1 (`TarjetaKpi` V1: código, semáforo, valor, tendencia, barra de avance a meta, meta, valor anterior y descripción). Cada una abre el drill-down `CmiDetalleKpi` (evolución por gestión).
- **Barra de filtros:** buscador (código o nombre), chips de semáforo (Verde, Ámbar, Rojo, Sin dato) y orden (brecha, nombre, código).
- **Abajo, gráficas según la perspectiva**, todas desde vistas `bi` ya existentes:

| Perspectiva | Gráficas |
|---|---|
| Financiera | Meta vs. ejecutado mensual (`bi.vw_metas_mensual`) · cartera por estado (`bi.vw_cartera_estado`) · avance a meta de sus KPI |
| Estudiantes y mercado | Inscritos por gestión/programa · conversión por fuente (si hay dato) · avance a meta |
| Procesos internos | Documentos por estado y confianza (`bi.vw_dataops_documento`) · avance a meta |
| Aprendizaje y crecimiento | Estudiantes en riesgo por nivel (`bi.vw_riesgo_estudiante`) · avance a meta |

- Backend: `GET /api/v1/cmi/perspectivas/{codigo}/detalle` devuelve series listas para graficar, devuelve 403 si la perspectiva no es visible para el rol y sin PII (`dim_estudiante` queda fuera).
- Enlace profundo: `/v2/dashboard?p=FINANCIERA`.

Criterios: (a) la búsqueda filtra en menos de 100 ms sin pedir datos de nuevo; (b) un estado vacío con motivo cuando no hay dato, nunca una cifra de relleno; (c) responsivo a 375, 768 y 1440 px; (d) tests de componentes (filtro, chips, volver) y de API (403 por rol). Salida: `rv2_l4_pruebas.txt` y `rv2_l4_capturas/`.

### L5 — Analítica predictiva reorganizada (`dev-media`) · skill `/data:data-context-extractor` primero
- **L5-0:** con `/data:data-context-extractor`, documentar en `docs/contexto_datos_prediccion.md` qué significa cada campo de `/forecast/analitica-macro` (caso1–caso4), qué es vital para el analista y qué invariante lo gobierna (HW amortiguado m = 12, hold-out 6; OLS mensual N = 40; OLS anual solo descriptiva).
- **Estructura nueva:**
  1. **Franja ejecutiva** de 4 cards: inscritos proyectados en el horizonte (con IC 95 %), calidad del modelo (MAPE · RMSE), cumplimiento proyectado del mes y avance de la meta anual.
  2. **Sub-pestañas** (`CachedSubTabsV2`): *Demanda* (caso 1) · *Programas* (caso 2, matriz de viabilidad con buscador, filtro por tipo y paginación) · *Metas mensuales* (caso 3) · *Tendencia anual* (caso 4, rotulada «descriptiva»).
  3. **Drill-down en panel lateral** (en lugar del modal en línea): tabla de la serie, nota metodológica y, en Programas, la ficha del programa (decisión sugerida, justificación, CAGR, proyección 6 m).
  4. El selector de horizonte se queda en la franja superior.

Criterios: (a) las cifras coinciden al 100 % con `rv2_l0_macro.json`; (b) la etiqueta «OLS anual — solo descriptiva» es visible en caso 4; (c) el drawer se cierra con Esc y devuelve el foco; (d) tests de componentes. Salida: `rv2_l5_cifras_vs_l0.json`.

### L6 — Botón Actualizar con animación + Sileo (`dev-baja`)
- Hook `useActualizarCmi()`: invalida `['cmi']` y, si el modo es Predictiva, `['analiticaPredictivaMacro']`; envuelve la promesa en `sileoToast.promise` (cargando: «Actualizando CMI…» → éxito: «CMI actualizado · 23 indicadores · hh:mm» → error con el mensaje de `utils/mensajeError.js`).
- Botón: el icono gira mientras `isFetching`, el botón queda desactivado y aparece un sello «Actualizado hace X min». Sin parpadeo de skeleton (se mantiene `keepPreviousData`).
- Evita el doble disparo (si ya hay un refresco en curso, no se lanza otro toast).

Criterios: (a) test: un clic produce un toast de carga y uno de éxito, y dos clics rápidos solo uno; (b) `prefers-reduced-motion` sin giro. Salida: `rv2_l6_pruebas.txt`.

### L7 — Configuración: roles, KPI y gráficas personalizadas · requiere D3, D4 y D6
**Diagnóstico actual:** la configuración es **solo ADMIN** (front `isAdmin` y back `require_roles(["ADMIN"])`), **solo edita** (no crea ni borra) y cada KPI tiene su fórmula fija en SQL dentro de `bi.vw_cmi_valores`. Desde la UI no se puede añadir un KPI real sin un motor de medidas.

| ID | Tarea | Agente | Criterio |
|---|---|---|---|
| L7-1 | **Diseño** (ADR corto en `docs/adr/ADR_rv2_kpi_graficos.md`): catálogo de medidas en lista blanca (vista `bi` + agregación + filtro + dimensión), almacenamiento según D3 y sin SQL libre | `dev-alta` | ADR aprobado por Lean |
| L7-2 | **Roles:** ADMIN edita todo; el analista (D4) edita meta, umbrales, peso y nombre **solo de las perspectivas que ve** (`VISIBILIDAD`). En el back, `require_roles([...])` + chequeo de perspectiva → 403 | `dev-media` | Tests: el analista financiero edita KPI-01 → 200 y KPI-07 → 403 |
| L7-3 | **KPI personalizados** (D3): crear, editar y archivar desde el catálogo de medidas; se marcan «Personalizado», van aparte de los 23 oficiales y **no entran al índice global** salvo otra decisión | `dev-media` | Los 23 KPI y el índice global quedan iguales a L0 |
| L7-4 | **Gráficas personalizadas** (D6), estilo constructor: fuente (vista `bi` permitida) → dimensión → medida → agregación → tipo (barras, línea, área, dona, tabla) → perspectiva destino. Vista previa en vivo y se muestran en el panel de L4 | `dev-media` | Una gráfica creada por el admin aparece en su perspectiva; un rol sin acceso no la ve |
| L7-5 | **UI de Configuración** con pestañas: Perspectivas · Indicadores · KPI personalizados · Gráficas. Auditoría de cada cambio (`actualizado_por`, `actualizado_en`) | `dev-media` | Tests de componentes y de API |

### L8 — Limpieza de archivos y código muerto (`dev-baja`) · requiere D5
Regla: **solo se borra lo que tiene 0 referencias** en `rv2_l0_inventario_limpieza.csv`, y después de cada borrado se corre build + vitest + pytest.

| Candidato | Estado | Propuesta |
|---|---|---|
| `frontend/borrador web/` (160 KB) | No versionado, sin referencias | Borrar |
| `__pycache__/` raíz, `.pytest_cache`, `.coverage` | Caché | Borrar (ya en `.gitignore`) |
| `node_modules/` en la raíz (2,2 MB) | No versionado | Verificar si la raíz tiene `package.json`; si no, borrar |
| `backend/uploads/` (44 KB) | No versionado | Revisar el contenido y borrarlo si son pruebas |
| `_archivo/` (138 archivos versionados, 4,7 MB) | Histórico | **D5** |
| `.agent/`, `.agents/`, `.codex/`, `AGENTS.md` | Config de otras herramientas | **D5** (no se borra sin tu OK) |
| `output/` (15 GB) | Modelos BETO y salidas | **No tocar** |
| `backups/*.dump` | Respaldos de BD | **No tocar** |
| Imports y estilos sin uso en `frontend/src` | Código | eslint `no-unused-vars` + búsqueda de clases CSS sin uso |

Criterio: build, vitest y pytest iguales a L0 (o mejores) y cada borrado registrado con su prueba de 0 referencias en `rv2_l8_borrados.csv`.

### L9 — Verificación final en navegador + cierre (`dev-baja`)
- Navegador en `/v2/dashboard`: los 3 modos (sin Power BI), 1440 / 768 / 375 px, claro y oscuro, roles ADMIN, ANALISTA_FINANCIERO y ANALISTA_MARKETING.
- 0 errores en consola, 0 llamadas a `/powerbi/*` en la red, capturas «después» junto a las de L0.
- Rebuild `web` y `api`; `docker compose ps` con 9 servicios arriba.
- Escribir `CIERRE_RV2.md`. Salida: `rv2_l9_capturas/` y `rv2_l9_consola_red.txt`.

---

## 3. Comandos exactos
```powershell
cd frontend; npx vitest run; npm run build
```
```powershell
.venv\Scripts\python -m pytest tests -q --cov=backend --cov-report=term
```
```powershell
$env:POSTGRES_PASSWORD = "<desde .env local, nunca versionado>"; docker compose up -d --build --no-deps web api
```
```powershell
git grep -niE "powerbi|power bi|pbix" -- backend frontend/src tests gateway infrastructure
```

## 4. Riesgos y control
- **Cifras:** L3, L4 y L5 solo muestran datos del DW. Se comparan contra los JSON de L0 y una cifra distinta bloquea el cierre del loop.
- **V1 compartida:** `CmiScorecard` y `CardFolderV2` también sirven a `/dashboard` (V1). Cada loop captura la V1 y verifica que no cambió.
- **Snapshot:** ningún loop escribe en `snapshot_dw_20261110_1201`; las migraciones nuevas se prueban primero en la copia tmpfs.
- **Paralelo:** L3, L5 y L6 solo van en paralelo después de L2, porque tocan archivos distintos (`scorecard/`, `prediccion/` y `CmiHeader.jsx`).
- **Colores:** solo tokens existentes de `tokens.css` y `v2-tokens.css`. Animaciones de 200–900 ms con `MOTION_EASING_CSS` y respeto de `prefers-reduced-motion`.

## 5. DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que respondas)
- **D1 — RESUELTA (Lean, 2026-11-20): opción (b).** Se retiran el código, el endpoint y los archivos de Power BI; `public.powerbi_informe_version` queda vacía y sin uso, y el invariante sigue en 51 tablas. En L1-3 no se crea `020_retirar_powerbi.sql` con `DROP TABLE`, la `007` sigue en `MIGRACIONES_EN_ARRANQUE` y la tabla se documenta como «sin uso, retirada de la UI» en el cierre. Su borrado se planifica junto con la próxima actualización del documento. Contexto original:
- ~~D1 — Power BI y el invariante «51 tablas».~~ `public.powerbi_informe_version` **cuenta dentro de las 51 tablas** (`f3v_invariantes.json` cuenta public + bi; la tabla figura en `diccionario_datos.csv`). Opciones: **(a)** borrarla → 50 tablas, y el chat 3 actualiza el documento y las figuras 3.2 y 3.3 de arquitectura y despliegue, que nombran Power BI; **(b)** retirar código, endpoint y archivos pero dejar la tabla vacía y sin uso → el invariante sigue en 51. *Recomendación: (b) ahora y (a) junto con la próxima actualización del documento.*
- **D2 — RESUELTA (Lean, 2026-11-20): borrar el rol.** L1-3 crea la migración `020_retirar_rol_powerbi_reader.sql`, idempotente y dentro de un bloque `DO` que solo actúa si el rol existe: `ALTER DEFAULT PRIVILEGES IN SCHEMA bi REVOKE SELECT ON TABLES FROM powerbi_reader` → `REVOKE ALL ON ALL TABLES IN SCHEMA bi` → `REVOKE USAGE ON SCHEMA bi` → `DROP OWNED BY powerbi_reader` → `DROP ROLE powerbi_reader`. Si falta privilegio, `RAISE NOTICE` (igual que en la 006). Se agrega al final de `MIGRACIONES_EN_ARRANQUE`; la `006` no se edita, así que en una instalación limpia la 006 crea el rol y la 020 lo borra. Se prueba primero en la copia tmpfs (nunca en el snapshot) y `test_migraciones_arranque.py` comprueba el orden. Criterio: `SELECT 1 FROM pg_roles WHERE rolname='powerbi_reader'` → 0 filas; la segunda corrida de la migración no da error. Las referencias en `_archivo/powerbi/` se tratan en D5. Contexto original:
- ~~D2 — Rol `powerbi_reader` de PostgreSQL:~~ ¿se borra (`DROP ROLE`) o se deja? *Recomendación: borrarlo en la misma migración que D1-a, o revocarle permisos si se elige D1-b.*
- **D3 — RESUELTA (Lean, 2026-11-20): esquema `app` nuevo.** L7 crea la migración `021_esquema_app_personalizacion.sql` (idempotente):
  - `CREATE SCHEMA IF NOT EXISTS app`.
  - `app.medida_catalogo`: lista blanca de medidas, con vista `bi` de origen, columna, agregación permitida y dimensiones permitidas. Se siembra desde la migración; la UI no la edita.
  - `app.kpi_personalizado`: código `KPP-nn` (no choca con `KPI-nn`), perspectiva, medida, filtro, unidad, sentido, meta, umbrales, estado (activo o archivado), creado y actualizado por.
  - `app.grafico_personalizado`: perspectiva, medida, dimensión, agregación, tipo, orden, visibilidad y autor.

  Reglas:
  - **Nada** de `app` entra en `bi.ref_kpi`, en `bi.vw_cmi_*` ni en el índice global. Los 23 KPI y las 51 tablas (public + bi) quedan intactos.
  - Criterio de L7: `f3v_invariantes` recalculado da 51 / 10 / 23, igual que L0 (`rv2_l7_invariantes.json`).
  - El back arma el SQL solo desde `app.medida_catalogo`, con identificadores en lista blanca y valores parametrizados. Nunca hay SQL libre del usuario.
  - El rol de la API recibe `USAGE` y DML sobre `app`.
  - `scripts/diccionario_datos_csv.py` e `inventario_tablas*.py` siguen filtrando public + bi. `app` se documenta aparte en el ADR de L7-1.

  Contexto original:
- ~~D3 — KPI personalizados y el invariante «23 KPI en `bi.ref_kpi`».~~ Opciones: **(a)** tabla aparte (`public.cmi_kpi_personalizado`) fuera del índice global (pero eso suma tablas al 51); **(b)** esquema nuevo `app` para la configuración de usuario, fuera del conteo public + bi; **(c)** no crear KPI y solo editar los 23. *Recomendación: (b).*
- **D4 — RESUELTA (Lean, 2026-11-20): ADMIN, ANALISTA_FINANCIERO y ANALISTA_MARKETING.**
  - **ADMIN:** edita todo (perspectivas, los 23 KPI, KPI personalizados y gráficas de las 4 perspectivas).
  - **ANALISTA_FINANCIERO:** solo la perspectiva FINANCIERA.
  - **ANALISTA_MARKETING:** solo CLIENTES.
  - Los analistas editan nombre, descripción, meta, umbrales, peso y activo de los KPI de su perspectiva, y crean, editan y archivan KPP y gráficas en ella. **No** editan la perspectiva (objetivo, pregunta, peso en el índice global): eso queda solo para ADMIN.
  - DIRECTOR_ACADEMICO y AUDITOR_CALIDAD siguen solo con lectura.
  - **Back:** `require_roles(["ADMIN","ANALISTA_FINANCIERO","ANALISTA_MARKETING"])` + chequeo `perspectiva ∈ VISIBILIDAD[rol]` → 403 si no.
  - **Front:** el botón Configuración se muestra para estos 3 roles y la pantalla solo lista sus perspectivas.
  - **Tests de L7-2:**
    - financiero edita KPI-01 → 200; KPI-07 → 403; PUT de perspectiva → 403;
    - marketing edita un KPI de CLIENTES → 200; uno FINANCIERO → 403;
    - director → 403 en todo PUT y POST.

  Contexto original:
- ~~D4 — ¿Qué es «el analista»?~~ ¿ANALISTA_FINANCIERO y ANALISTA_MARKETING (cada uno solo su perspectiva)? ¿También DIRECTOR_ACADEMICO?
- **D5 — RESUELTA (Lean, 2026-11-20): borrar lo de Power BI y conservar el resto.** Pasa a **L1-4** (no espera a L8):
  - **Se borra:** `_archivo/powerbi/` completo, con sus 6 archivos versionados: `01_power_query.pq`, `02_medidas_cmi.dax`, `03_tema_giragroup_cmi.json`, `04_tabular_editor.cs`, `05_generar_paginas.py` y `README.md`. Esto se suma a `powerbi/dashboards/` y `uploads/powerbi/`.
  - **Se conserva:** el resto de `_archivo/` y `.agent/`, `.agents/`, `.codex/` y `AGENTS.md`, que no mencionan Power BI.
  - **No se editan** los archivos históricos que solo *nombran* Power BI dentro de un registro: `_archivo/docs/evidencias/RESUMEN_RONDA9.md`, `cobertura_ronda6.json`, `regresion_s3/pytest_cov.txt`, `_archivo/raiz/diccionario_datos.csv` y `fuente_verdad_tesis.md`, los `CIERRE_*`/`PLAN_*` previos, `docs/mediciones/` y `docs/evidencias/`. Son registros de lo que pasó y no se reescriben.
  - **Criterio L1:** `git ls-files | grep -iE "powerbi|pbix"` = 0. El grep de L1-1/L1-2 da 0 en código vivo; solo quedan menciones en registros históricos y en los nombres de programa del catálogo (`rv2_l1_grep_powerbi.txt` las lista y justifica una por una).

  Contexto original:
- ~~D5 — `_archivo/`~~ (138 archivos versionados) y `.agent/`, `.agents/`, `.codex/`, `AGENTS.md`:** ¿se borran, se mueven fuera del repo o se quedan?
- **D6 — RESUELTA (Lean, 2026-11-20): vistas `bi` + tablas de hechos.** `app.medida_catalogo` admite como origen las 10 vistas `bi` y los 10 hechos `fact_*`. Controles obligatorios en L7-1 (ADR) y L7-4:
  - **Lista blanca:** solo columnas numéricas de los hechos (medidas) y joins a dimensiones **sin PII** (tiempo, programa, módulo, modalidad, fuente). `dim_estudiante` y toda columna de nombre, CI, correo o teléfono quedan **fuera** del catálogo; un test recorre el catálogo y falla si aparece alguna.
  - **Solo agregados:** SUM, AVG, COUNT, COUNT DISTINCT, MIN y MAX agrupados por una dimensión, nunca filas sueltas. Los grupos con menos de 5 registros se ocultan (salen como «< 5»), para que nadie identifique a un estudiante.
  - **Alcance por rol:** cada medida va atada a una perspectiva, y un analista solo ve las medidas de su perspectiva (D4).
  - **Rendimiento:** la consulta corre en transacción de solo lectura (`SET TRANSACTION READ ONLY`) con `statement_timeout` de 5 s, `LIMIT` de 500 grupos y caché de 60 s (`cache_consultas`).
  - **Sin escritura:** el constructor nunca escribe en `public` ni en `bi`.
  - **Criterios L7-4:**
    - test de lista blanca sin PII → passed;
    - test de grupo menor a 5 → oculto;
    - test de timeout → 504 con mensaje claro;
    - una gráfica sobre un hecho cuadra con la misma consulta SQL hecha a mano (`rv2_l7_grafico_vs_sql.json`).

  Contexto original:
- ~~D6 — Gráficas personalizadas:~~ ¿solo vistas `bi` en lista blanca, sin PII (recomendado), o también tablas de hechos?

Al cerrar cada loop: vitest + pytest con cobertura · rebuild de lo tocado · commit `rv2(L<n>): …` · `CIERRE_RV2_L<n>.md`.

---

## PROMPT PARA CHAT 2 (uno por loop; cambiar `L<n>`)
```
/gira-desarrollar
Ejecuta SOLO el loop L<n> de docs/cierres/REESTRUCTURACION_VISTA_V2.md (secciones 2, 3 y 4).
- No avances al loop siguiente; cierra con docs/cierres/CIERRE_RV2_L<n>.md.
- Respeta los invariantes de CLAUDE.md; si un paso toca una DECISIÓN PENDIENTE sin respuesta escrita de Lean, detente.
- Cifras: compara contra docs/mediciones/rv2_l0_*.json; una diferencia bloquea el cierre.
- Usa los skills indicados en el loop (/frontend-design, dataviz, /data:build-dashboard, /data:data-context-extractor).
- Solo tokens de color existentes; animaciones con MOTION_EASING_CSS y prefers-reduced-motion.
- Al final: vitest + build + pytest, rebuild de web/api y commit rv2(L<n>).
```
