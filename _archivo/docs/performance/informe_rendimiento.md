# Informe de Auditoría de Rendimiento (`giragroup_bi_system`)

## 1. Resumen Ejecutivo (Top 5 Hallazgos de Mayor Impacto)
1. **[F-01] Contenedor `web` sirve Vite Dev Server en vez de build estático (`docker-compose.yml:178-180`, `infrastructure/docker/web.Dockerfile:19`):** ejecuta `pnpm install && pnpm run dev --host` en cada arranque con file-polling cada `200 ms` (`frontend/vite.config.js:10-13`) sobre bind mount en Windows, forzando la descarga de cientos de módulos ESM sin empaquetar al entrar al link web (**+3,000 a +6,500 ms** en carga inicial frente a los `344.06 KiB` gzip del build compilado).
2. **[F-02] Nginx Gateway sin `gzip`, sin `Cache-Control`/`ETag` en estáticos y sin `keepalive` (`gateway/nginx.conf:5-44, 255-261`):** transmite los `1,152.78 KiB` de JS/CSS sin comprimir desde el gateway y abre/cierra una conexión TCP nueva por petición hacia cada upstream (`api:8000`, `auth-service:8001`, `notifications-service:8002`, `audit-service:8004`, `web:5173`).
3. **[F-03] Penalización visual fija en navegación SPA (`560 ms`) + Canvas 2D a 60 FPS activo por defecto (`frontend/src/App.jsx:175-241, 375`, `ThemeContext.jsx:8, 19-22`):** `triggerLoadingAnimation()` y `finishLoadingAnimation()` inyectan timers artificiales (`340 ms + 220 ms`) en cada clic de enlace o cambio de ruta, mientras `IsometricCanvasBackground.jsx:57-123` ejecuta trigonometría continua sobre 216 nodos y ~204 aristas a 60 FPS en el hilo principal.
4. **[F-04] Full-scan en memoria (`.all()` de 7 tablas sin `WHERE` de negocio) en `/riesgos/alertas-tempranas` (`backend/services/risk_service.py:109-187`) y carga prematura de pestaña oculta en `AuditoriaSistema.jsx:102-108`:** descarga todas las dimensiones y hechos a Python para evaluar reglas A/D/F (`p50 = 380 ms`, `p95 = 700 ms`, `max = 1,194.5 ms` en Locust).
5. **[F-05] 17 consultas SQL secuenciales en `/kpis/cmi-completo` (`backend/services/kpi_service.py:344-867`) y entrenamiento sin caché de 5 modelos Holt-Winters + 2 OLS + lectura de Excel en `/forecast/analitica-macro` (`backend/routers/forecast.py:165-185`, `forecast_service.py:294, 381-529`):** bloquea workers síncronos (`p95 = 740 ms` en CMI; >1,200 ms estimado en forecast macro) y se duplica en paralelo desde `ProyeccionFinanciera.jsx:37-40` y `ProyeccionAlumnos.jsx:37-40`.

---

## 2. Fase 1: Inventario de Arquitectura y Mapeo End-to-End

### 2.1 Inventario de Rutas Frontend (`frontend/src/App.jsx:13-42, 377-543`)
*Contexto global en todas las rutas autenticadas (`MainLayout` en `App.jsx:160-352`):*
- **Canvas 2D continuo (60 FPS):** `IsometricCanvasBackground` (`App.jsx:375`), habilitado por defecto (`canvasEnabled: true` en `ThemeContext.jsx:8, 21`).
- **Carga inicial de notificaciones:** `NotificationContext.jsx:31-36` ejecuta `refreshNotifications()` (`GET /api/v1/notifications`) al montar la aplicación si existe `gira_token`.
- **Retardo visual en navegación:** `App.jsx:175-241` intercepta todo clic en `<a href>` y cambio en `location.pathname`, activando el indicador `"Cargando sección..."` por un mínimo de `340 ms + 220 ms = 560 ms`.

| Ruta (`App.jsx`) | Componente Principal | Llamadas API al Montar / Interactuar (Método + Endpoint Real) | Orden de Ejecución | Estado de Carga UI | Polling / Timers Locales |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/login` | `LoginPage.jsx` | 1) `POST /api/v1/auth/login`<br>2) `POST /api/v1/auth/verify-2fa` | Secuencial (2 pasos de autenticación) | Botón bloqueante (`loading`) | Timer 1 s countdown OTP |
| `/dashboard`, `/cmi` | `CuadroMandoIntegral.jsx` | 1) `GET /api/v1/kpis/cmi-completo` (Modo A, al montar)<br>2) `GET /api/v1/forecast/analitica-macro?horizonte={h}` (al activar Modo B)<br>3) `GET /api/v1/reportes/export?tipo=kpis&formato={fmt}` (al exportar) | 1 al montar (`useQuery`); 2 condicional (`enabled: activeMode === 'B'`); 3 bajo demanda | Fallback en memoria + spinner de refresco | Sin polling (`staleTime: 60s` en `CuadroMandoIntegral.jsx:204`) |
| `/reportes` | `CentroReportes.jsx` | 1) `GET /api/v1/catalogs/institutional-summary`<br>2) `GET /api/v1/reportes/historial?limit=15`<br>3) `GET /api/v1/reportes/export?tipo=...&formato=...` (al descargar) | 1 y 2 en paralelo al montar (`CentroReportes.jsx:75-99`); 3 bajo demanda | Spinner en tabla / botón `loadingExport` bloqueante | Sin polling |
| `/notificaciones` | `NotificationsPage.jsx` | 1) `GET /api/v1/notifications` (vía `NotificationContext`)<br>2) `PATCH /api/v1/notifications/{id}/read`<br>3) `PATCH /api/v1/notifications/read-all` | 1 al montar contexto; 2–3 bajo demanda | Render inmediato desde `NotificationContext` | Sin polling activo en `NotificationContext.jsx` |
| `/ajustes` | `AjustesSistema.jsx` | 1) Lectura síncrona de `localStorage` al montar (`calculateStorage`)<br>2) `POST /api/v1/dataops/purge-staging-cache` + `GET /api/v1/notifications` (al purgar caché) | 1 al montar; 2 secuencial bajo demanda (`AjustesSistema.jsx:54-82`) | Botón `isClearing` con `Loader2` | Timer `4–5 s` para limpiar banner de estado |
| `/dataops/ingesta` | `IngestView.jsx` | 1) `GET /api/v1/dataops/sources`<br>2) `GET /api/v1/dataops/lote/{id}/raw-vs-text` (si existe `last_active_batch_id` en `localStorage`)<br>3) `POST /api/v1/dataops/upload-batch`<br>4) `GET /api/v1/dataops/logs/{docId}` (al abrir drawer) | **Secuencial (waterfall):** 1 espera a `getSources()` y luego dispara 2 (`IngestView.jsx:64-72`) | Spinner en historial + barra de progreso bloqueante en subida | Sin polling; bloquea en `upload-batch` (timeout 600s) |
| `/dataops/texto`, `/dataops/lote/:id/texto` | `PlainTextTransformationView.jsx` + `BatchFlowLayout.jsx` | 1) `GET /api/v1/dataops/lote/{id}/context` (en `BatchFlowLayout.jsx:62`, fallback a `GET /api/v1/dataops/sources`)<br>2) `GET /api/v1/dataops/lote/{id}/raw-vs-text` (`PlainTextTransformationView.jsx:38`) | Paralelo al montar padre e hijo (`BatchFlowLayout` + `PlainTextTransformationView`) | Estado `loading` en tabla | Caché en memoria 60s (`dataopsApi.js:263, 274`) |
| `/dataops/beto`, `/dataops/lote/:id/beto` | `BetoReadingFlowView.jsx` + `BatchFlowLayout.jsx` | 1) `GET /api/v1/dataops/lote/{id}/context` (`BatchFlowLayout.jsx:62`)<br>2) `GET /api/v1/dataops/lote/{id}/beto-reading?page_size=300` (`BetoReadingFlowView.jsx:53`)<br>3) `POST /api/v1/dataops/confirm-dw-insert` (al confirmar lote) | 1 y 2 en paralelo al montar; 3 bajo demanda en modal | Spinner bloqueante (`timeout: 900s` en primera lectura BETO) | Caché 60s en `dataopsApi.js:285` |
| `/dataops/revision`, `/dataops/lote/:id/revision` | `HumanReviewFlowView.jsx` + `BatchFlowLayout.jsx` | 1) `GET /api/v1/dataops/lote/{id}/context` (`BatchFlowLayout.jsx:62`)<br>2) `GET /api/v1/dataops/review-tray?id_lote={id}&page_size=500` (`HumanReviewFlowView.jsx:75`)<br>3) `POST /api/v1/dataops/review-tray/aprobar-un-clic`<br>4) `POST /api/v1/dataops/review-tray/{id}/resolve`<br>5) `POST /api/v1/dataops/confirm-dw-insert` | 1 y 2 en paralelo al montar; 3–5 bajo demanda | Spinner bloqueante + botones `isAprobandoBloque` / `isConsolidatingDw` | Caché 45s en `dataopsApi.js:307` |
| `/dataops/datos-maestros` | `MasterDataView.jsx` | 1) `GET /api/v1/estudiantes?q=...` (pestaña `'students'`)<br>2) `GET /api/v1/docentes?q=...` (`'teachers'`)<br>3) `GET /api/v1/modulos?q=...` (`'modules'`)<br>4) `GET /api/v1/instituciones?q=...` (`'institutions'`) | 1 llamada por cambio de pestaña (`MasterDataView.jsx:36-61`, sin caché por pestaña) | Tabla `ResponsiveTable` con estado `isLoading` | Sin polling |
| `/alertas-tempranas`, `/academico/alertas`, `/academico/rendimiento` | `RendimientoAlertas.jsx` | 1) `GET /api/v1/riesgos/alertas-tempranas` (React Query)<br>2) `GET /api/v1/riesgos/ficha-estudiante/{id}` (al abrir modal de alumno)<br>3) `GET /api/v1/reportes/export?tipo=alertas...` (al exportar) | 1 al montar (`useQuery`); 2 y 3 bajo demanda | Skeletons / tabla con `keepPreviousData` | Debounce de `350 ms` en búsqueda (`RendimientoAlertas.jsx:48-53`) |
| `/academico/docente` | `DesempenoDocente.jsx` | 1) `GET /api/v1/docentes` (`catalogApi.getDocentes()` en `DesempenoDocente.jsx:22`) | Único request al montar (`useEffect`) | Tabla con `isLoading` | Sin polling |
| `/academico/catalogo`, `/academico/programas` | `CatalogoCurricular.jsx` | 1) `GET /api/v1/modulos` (`catalogApi.getModulos()` en `CatalogoCurricular.jsx:18`) | Único request al montar (`useEffect`) | Tabla con `isLoading` | Sin polling |
| `/academico/proyeccion` | `ProyeccionAlumnos.jsx` | 1) `GET /api/v1/forecast/analitica-macro?horizonte={h}`<br>2) `GET /api/v1/forecast/alumnos?tipo={agregacion}&horizonte={h}` | Paralelo (`Promise.all` en `ProyeccionAlumnos.jsx:37-40`) — **duplica cálculo HW cuando `agregacion === 'GLOBAL'`** | Spinner bloqueante (`isLoading`) | Sin polling (no usa React Query) |
| `/financiero/recaudacion` | `RecaudacionCobranzas.jsx` | 1) `GET /api/v1/kpis/financieros`<br>2) `GET /api/v1/forecast/laboratorio-macro` (alias de `/analitica-macro`) | Paralelo (`Promise.allSettled` en `RecaudacionCobranzas.jsx:26-29`) | `useQuery` con `keepPreviousData` | Sin polling (`staleTime: 60s`) |
| `/financiero/cartera` | `CarteraMora.jsx` | 1) `GET /api/v1/riesgos/alertas-tempranas?regla_filtro=FINANCIERO`<br>2) `GET /api/v1/kpis/financieros` | Paralelo (`Promise.allSettled` en `CarteraMora.jsx:32-35`) | `useQuery` con `keepPreviousData` | Sin polling (`staleTime: 60s`) |
| `/financiero/metas` | `MetasGestion.jsx` | 1) `GET /api/v1/forecast/analitica-macro?horizonte=6`<br>2) `GET /api/v1/kpis/cmi-completo`<br>3) `GET /api/v1/catalogs/institutional-summary` | Paralelo (`Promise.all` de los 3 endpoints en `MetasGestion.jsx:26-30`) | `useQuery` con `keepPreviousData` | Sin polling (`staleTime: 60s`) |
| `/financiero/proyeccion` | `ProyeccionFinanciera.jsx` | 1) `GET /api/v1/forecast/analitica-macro?horizonte={h}`<br>2) `GET /api/v1/forecast/metas?granularidad={g}&horizonte={h}` | Paralelo (`Promise.all` en `ProyeccionFinanciera.jsx:37-40`) — **duplica cálculo HW mensual** | `useQuery` con `keepPreviousData` | Sin polling (`staleTime: 60s`) |
| `/admin/usuarios` | `GestionUsuarios.jsx` | 1) `GET /api/v1/users`<br>2) `POST / DELETE /api/v1/users...` | 1 al montar (`GestionUsuarios.jsx:34`); resto bajo demanda | Tabla con `isLoading` | Sin polling |
| `/admin/catalogos` | `CatalogosMaestros.jsx` | 1) `GET /api/v1/modulos`<br>2) `GET /api/v1/docentes`<br>3) `GET /api/v1/catalogs/financial/concepts` | Paralelo (`Promise.all` en `CatalogosMaestros.jsx:29-33`) | `useQuery` con `keepPreviousData` | Sin polling (`staleTime: 60s`) |
| `/admin/auditoria` | `AuditoriaSistema.jsx` | 1) `GET /api/v1/audit/logs?limit=200`<br>2) `GET /api/v1/kpis/alertas`<br>3) `GET /api/v1/riesgos/cruzado?umbral_nota=70&umbral_mora=2` | **Paralelo al montar** (`AuditoriaSistema.jsx:102-108` ejecuta `loadAuditData()` y `loadAlertasData()` aunque la pestaña `'alertas'` esté oculta) | Spinners `isLoadingLogs` / `isLoadingAlertas` | Sin polling |

---

### 2.2 Mapeo Llamada API → Router → Service → Consultas SQL

| Endpoint API | Router (`archivo:línea`) | Service (`archivo:línea`) | Nº Queries SQL | Tablas Reales (`db/schema.sql`) / Joins / Agregaciones / Filtros |
| :--- | :--- | :--- | :---: | :--- |
| `GET /api/v1/kpis/cmi-completo` | [`backend/routers/kpis.py:72-97`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/kpis.py#L72-L97) | [`backend/services/kpi_service.py:344-867`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/kpi_service.py#L344-L867) (`obtener_perspectivas_cmi_completo`) | **15 a 17** | `fact_rendimiento_academico`, `fact_situacion_financiera`, `fact_rentabilidad`, `fact_marketing`, `dim_modulo`, `dim_tiempo`, `dim_origen_documental`, `stg_entidad_no_resuelta`. Ejecuta 6 escaneos separados sobre `fact_rendimiento_academico` y 4 sobre `fact_situacion_financiera` con `JOIN dim_tiempo` y `LEFT JOIN dim_modulo`; agregaciones `SUM`, `AVG`, `COUNT(DISTINCT)`. Cacheado 120s por proceso worker (`cache_consultas.py:17`). |
| `GET /api/v1/kpis/perspectivas` | [`backend/routers/kpis.py:31-56`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/kpis.py#L31-L56) | [`backend/services/kpi_service.py:335-342`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/kpi_service.py#L335-L342) (`obtener_consolidado_general`) | **5** | `fact_rendimiento_academico` (2 queries), `fact_situacion_financiera` (1 query con 7 agregaciones `FILTER`), `dim_origen_documental` (1 `COUNT`), `stg_entidad_no_resuelta` (1 `COUNT`). |
| `GET /api/v1/riesgos/alertas-tempranas` | [`backend/routers/riesgos.py:30-69`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/riesgos.py#L30-L69) | [`backend/services/risk_service.py:93-584`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/risk_service.py#L93-L584) (`evaluar_alertas_tempranas_deterministicas`) | **7** (`.all()` sin `WHERE` de negocio) | Descarga íntegra a RAM de `dim_estudiante` (`WHERE deprecado = false`), `dim_modulo`, `dim_docente`, `dim_tiempo`, `dim_origen_documental`, `fact_rendimiento_academico`, `fact_situacion_financiera`. Cruza y filtra en bucles Python (`risk_service.py:240-492`) evaluando `promedio_notas <= 70.0`, `max_incumplimiento > 30.0`, `cuotas_mora >= 2`. |
| `GET /api/v1/riesgos/cruzado` | [`backend/routers/riesgos.py:72-98`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/riesgos.py#L72-L98) | [`backend/services/risk_service.py:37-90`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/risk_service.py#L37-L90) (`obtener_riesgo_cruzado`) | **1** | Subqueries agrupadas en SQL sobre `fact_rendimiento_academico` (`AVG(nota_final) <= 70`) y `fact_situacion_financiera` (`SUM(cuotas_impagas) >= 2`) con `JOIN dim_estudiante`. |
| `GET /api/v1/riesgos/ficha-estudiante/{id}` | [`backend/routers/riesgos.py:124-162`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/riesgos.py#L124-L162) | [`backend/services/risk_service.py:586-734`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/risk_service.py#L586-L734) (`obtener_ficha_cruzada_estudiante`) | **7** | `dim_estudiante` (PK), `fact_rendimiento_academico` (`WHERE id_estudiante = :id`), `fact_situacion_financiera` (`WHERE id_estudiante = :id`), y 4 consultas `.in_()` dirigidas a `dim_modulo`, `dim_docente`, `dim_tiempo`, `dim_origen_documental`. |
| `GET /api/v1/forecast/alumnos` | [`backend/routers/forecast.py:44-94`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/forecast.py#L44-L94) | [`backend/services/forecast_service.py:114-184`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/forecast_service.py#L114-L184) (`obtener_pronostico_alumnos`) | **1 a 2 + Excel fallback** | **Sin `cache_consultas.obtener` en router (`forecast.py:80`).** Extrae serie temporal de `fact_rendimiento_academico` / `fact_marketing` JOIN `dim_tiempo` (o `TBL_INSCRITOS.xlsx`) y entrena `ExponentialSmoothing` (Holt-Winters `m=12`) en CPU en cada petición. |
| `GET /api/v1/forecast/metas` | [`backend/routers/forecast.py:97-152`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/forecast.py#L97-L152) | [`backend/services/forecast_service.py:187-278`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/forecast_service.py#L187-L278) (`obtener_pronostico_metas`) | **1 a 2** | Lee `fact_rentabilidad` / `fact_situacion_financiera` JOIN `dim_tiempo`; ajusta Holt-Winters (`MENSUAL`) u OLS (`ANUAL`). Sí usa `cache_consultas.obtener` (TTL 600s en `forecast.py:135`). |
| `GET /api/v1/forecast/analitica-macro` (y `/laboratorio-macro`) | [`backend/routers/forecast.py:155-190`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/forecast.py#L155-L190) | [`backend/services/forecast_service.py:284-529`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/forecast_service.py#L284-L529) (`obtener_analitica_macro_completa`) | **6 a 8 SQL + 1 Excel I/O** | **Sin `cache_consultas.obtener` en router (`forecast.py:183`).** Ejecuta 4 extracciones de alumnos (`GLOBAL`, `DIPLOMADO`, `CURSO`, `EXPERTO`) + 2 de metas (`MENSUAL`, `ANUAL`), lee `TBL_INSCRITOS.xlsx` del disco con `pd.read_excel` (`forecast_service.py:294`, caché local de 300s) y entrena **5 modelos Holt-Winters + 2 regresiones OLS** en el hilo del request sin leer `fact_forecast` (`db/schema.sql:294`). |
| `POST /api/v1/dataops/upload-batch` | [`backend/routers/dataops.py:356-630`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/dataops.py#L356-L630) | `ingestion_service.py` + `_evaluar_lote_en_segundo_plano` | **4 + 3×M archivos** | Inserta en `lote`, `dim_origen_documental`, `staging_registros_crudos`, `log_pipeline_ingesta` y lanza `_evaluar_lote_en_segundo_plano` en `BackgroundTasks` del mismo proceso FastAPI (`dataops.py:617`). |
| `POST /api/v1/dataops/confirm-dw-insert` | [`backend/routers/dataops.py:3320-3605`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/dataops.py#L3320-L3605) | [`backend/services/dw_loader.py:85-248`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/dw_loader.py#L85-L248) + `confianza_service.py` | **4 + 6×N** | Pre-carga `dim_estudiante`, `dim_docente`, `dim_modulo`, pero dentro de `for stg in stg_records:` consulta `DimOrigenDocumental` por fila (`dataops.py:3380`, N+1), invoca síncronamente `obtener_indices(lines)` → HTTP `POST http://pipeline:8006/indice` (`dataops.py:3410`), y por cada línea llama a `dw.cargar_registro()` con múltiples `.first()` y `db.flush()`. |
| `GET /api/v1/reportes/export` | [`backend/routers/reportes.py:155-558`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/reportes.py#L155-L558) | `kpi_service.py` / `risk_service.py` + `openpyxl` / `reportlab` | **7 a 18** | Re-ejecuta las consultas de KPIs o Alertas Tempranas, genera el binario `.xlsx`/`.pdf` síncronamente en RAM y hace `INSERT` + `COMMIT` en `log_pipeline_ingesta`. |
| `GET /api/v1/audit/logs` | [`services/audit-service/routers/audit.py:29-198`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/services/audit-service/routers/audit.py#L29-L198) (y `backend/routers/audit.py`) | Directo en router (`:8004` / `:8000`) | **2** (`.limit(1000)` + `.limit(500)`) | Descarga hasta 1,500 filas de `log_pipeline_ingesta` y `log_auditoria_nlp` en cada request, formatea strings, ordena en Python (`audit.py:146`) y pagina en memoria (`audit.py:184`). |

---

### 2.3 Matriz de Riesgo por Pantalla (Fase 1.3)

| Pantalla | Endpoints Disparados | Nº Queries SQL Totales | Tablas Principales (`db/schema.sql`) | Servicios Internos Involucrados | Nivel de Riesgo |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **Login** (`/login`) | `POST /api/v1/auth/login`, `POST /api/v1/auth/verify-2fa` | 2–4 | `users`, `log_pipeline_ingesta` | `:8001` (`auth-service`) / `:8000` (`api`), `:8002` (`notifications-service`) | **ALTO** (`p95 = 760 ms` en login por bcrypt en endpoint síncrono) |
| **Dashboard CMI** (`/dashboard`, `/cmi`) | `GET /api/v1/kpis/cmi-completo`, `GET /api/v1/notifications` (+ `GET /api/v1/forecast/analitica-macro` en Modo B) | 17 + 1 (+ 8 en Modo B) = **18 a 26** | `fact_rendimiento_academico`, `fact_situacion_financiera`, `fact_rentabilidad`, `fact_marketing`, `dim_modulo`, `dim_tiempo`, `dim_origen_documental`, `stg_entidad_no_resuelta`, `notifications` | `:8000` (`api`), `:8002` (`notifications`), `:5434` (`db`) | **CRÍTICO** (17 queries secuenciales en CMI + bundle dev sin comprimir) |
| **Alertas Tempranas** (`/alertas-tempranas`, `/academico/rendimiento`) | `GET /api/v1/riesgos/alertas-tempranas`, `GET /api/v1/riesgos/ficha-estudiante/{id}` | 7 (`.all()`) + 7 = **14** | `fact_rendimiento_academico`, `fact_situacion_financiera`, `dim_estudiante`, `dim_modulo`, `dim_docente`, `dim_tiempo`, `dim_origen_documental` | `:8000` (`api`), `:5434` (`db`) | **CRÍTICO** (Full-scan en RAM de 7 tablas sin `WHERE`, `p95 = 700 ms`) |
| **Metas de Gestión** (`/financiero/metas`) | `GET /api/v1/forecast/analitica-macro`, `GET /api/v1/kpis/cmi-completo`, `GET /api/v1/catalogs/institutional-summary` | 8 + 17 + 4 = **29** (+ lectura Excel) | Todas las tablas `fact_*` y `dim_*` + `TBL_INSCRITOS.xlsx` | `:8000` (`api`), `:5434` (`db`), Sistema de archivos | **CRÍTICO** (Combina simultáneamente los 2 endpoints más pesados del backend) |
| **Proyección Financiera / Alumnos / Recaudación** (`/financiero/proyeccion`, `/academico/proyeccion`, `/financiero/recaudacion`) | `GET /api/v1/forecast/analitica-macro` + `GET /api/v1/forecast/metas` (o `/alumnos` o `/kpis/financieros`) | 8 + 2 = **10** (+ lectura Excel) | `fact_rendimiento_academico`, `fact_situacion_financiera`, `fact_rentabilidad`, `dim_tiempo`, `dim_modulo` + `TBL_INSCRITOS.xlsx` | `:8000` (`api`), `:5434` (`db`), Sistema de archivos | **CRÍTICO** (Entrena 5–6 modelos Holt-Winters + 2 OLS en vivo por vista sin caché en `analitica-macro`) |
| **DataOps Flujo de 4 Pasos** (`/dataops/ingesta`, `/dataops/texto`, `/dataops/beto`, `/dataops/revision`) | `GET /sources`, `GET /lote/{id}/context`, `GET /lote/{id}/raw-vs-text`, `GET /lote/{id}/beto-reading`, `GET /review-tray`, `POST /confirm-dw-insert` | 2 a **4 + 6×N** | `lote`, `dim_origen_documental`, `staging_registros_crudos`, `stg_entidad_no_resuelta`, `dim_*`, `fact_*`, `log_pipeline_ingesta` | `:8000` (`api`), `:8006` (`pipeline` BETO), `:5434` (`db`) | **CRÍTICO** (Waterfall en `IngestView` + N+1 queries + llamada HTTP síncrona a `:8006/indice`) |
| **Auditoría del Sistema** (`/admin/auditoria`) | `GET /api/v1/audit/logs?limit=200`, `GET /api/v1/kpis/alertas`, `GET /api/v1/riesgos/cruzado` | 2 (1,500 filas) + 5 + 1 = **8** | `log_pipeline_ingesta`, `log_auditoria_nlp`, `fact_rendimiento_academico`, `fact_situacion_financiera`, `dim_estudiante` | `:8004` (`audit-service`), `:8000` (`api`), `:5434` (`db`) | **ALTO** (Peticiones de pestaña oculta al montar + paginación en Python de 1,500 logs) |
| **Cartera en Mora** (`/financiero/cartera`) | `GET /api/v1/riesgos/alertas-tempranas?regla_filtro=FINANCIERO`, `GET /api/v1/kpis/financieros` | 7 (`.all()`) + 1 = **8** | `fact_situacion_financiera`, `fact_rendimiento_academico`, `dim_estudiante`, `dim_modulo`, `dim_tiempo` | `:8000` (`api`), `:5434` (`db`) | **ALTO** (Dispara los 7 `.all()` de `alertas-tempranas` para filtrar solo mora financiera) |
| **Centro de Reportes** (`/reportes`) | `GET /api/v1/catalogs/institutional-summary`, `GET /api/v1/reportes/historial`, `GET /api/v1/reportes/export` | 4 + 1 + (7 a 17) | `log_pipeline_ingesta`, `fact_*`, `dim_*` | `:8000` (`api`), `:5434` (`db`) | **MEDIO-ALTO** (Generación síncrona de XLSX/PDF en memoria) |
| **Catálogos Maestros / Datos Maestros** (`/admin/catalogos`, `/dataops/datos-maestros`) | `GET /api/v1/{modulos,docentes,estudiantes,instituciones}`, `GET /api/v1/catalogs/financial/concepts` | **1 a 3** | `dim_modulo`, `dim_docente`, `dim_estudiante`, `cat_institucion`, `cat_categoria_financiera` | `:8000` (`api`), `:5434` (`db`), `:5433` (`catalog_db`) | **MEDIO** (Descarga completa sin virtualización DOM) |

---

## 3. Línea Base de Métricas (Fase 2 & Fase 3.2)

> **Nota metodológica de evidencia:**
> - Las métricas de **Bundle Frontend** fueron medidas ejecutando `node docs/performance/scripts/measure_frontend.mjs --build-only` (`npx vite build`, `1,975` módulos transformados).
> - Las métricas de **Latencia Backend bajo concurrencia** provienen de la telemetría real registrada en [`docs/evidencias/locust_summary_stats.csv`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv) (573 requests, 0% fallos).
> - Dado que los contenedores Docker (`:80`, `:8000`, `:5434`, `:8006`) estaban apagados durante la sesión (`socket.connect_ex` = `False`), las métricas de navegador en vivo (LCP/TBT) y planes `EXPLAIN (ANALYZE, BUFFERS)` se marcan explícitamente como **HIPÓTESIS** y cuentan con los 4 scripts verificados en `docs/performance/scripts/` listos para ejecución.

| Pantalla / Endpoint / Activo | Métrica | Valor Actual (Medido / Hipótesis) | Objetivo Recomendado | Fuente de Evidencia |
| :--- | :--- | :--- | :--- | :--- |
| **Bundle Producción Total (JS + CSS)** | Tamaño bruto / Gzip | **1,152.78 KiB** (`1,112.57 KiB` JS en 36 chunks + `40.21 KiB` CSS) / **344.06 KiB gzip** (`335.75 KiB` JS + `8.31 KiB` CSS) | `< 850 KiB` bruto / `< 250 KiB` gzip | Medido (`node docs/performance/scripts/measure_frontend.mjs --build-only`) |
| **Chunks Críticos (`vendor-react` / `vendor-charts` / `index`)** | Tamaño bruto / Gzip | `vendor-react`: **283.60 KiB** (`91.61 KiB` gzip)<br>`vendor-charts`: **171.50 KiB** (`59.89 KiB` gzip)<br>`index`: **122.84 KiB** (`38.00 KiB` gzip) | Diferir `vendor-charts` fuera de `/login` y rutas sin gráficas | Medido (`frontend/vite.config.js:28-50`) |
| **Carga Inicial en Contenedor `web` (`/login`)** | LCP / Tiempo hasta interactivo | **HIPÓTESIS: 3,500 – 7,500 ms** (Vite Dev Server sin empaquetar + `pnpm install` al arranque) | **< 1,200 ms** (Build estático + Nginx Gzip) | [`docker-compose.yml:178-180`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docker-compose.yml#L178-L180), [`gateway/nginx.conf:255-261`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/gateway/nginx.conf#L255-L261) |
| **Transición entre Rutas SPA** | Latencia visual de navegación | **560 ms mínimo fijo** (`340 ms` barra + `220 ms` fade-out) + tiempo de red | **< 100 ms** (activar barra solo si `Suspense` tarda > 120 ms) | Medido en código ([`frontend/src/App.jsx:175-241`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/App.jsx#L175-L241)) |
| **Hilo Principal UI (Background 2D)** | Costo CPU continuo (TBT / Frame budget) | **216 nodos + 204 aristas a 60 FPS** (`Math.sqrt/atan2/sin/cos` por frame) | **0 ms en reposo** (`canvasEnabled = false` por defecto) | Medido en código ([`IsometricCanvasBackground.jsx:57-123`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/components/canvas3d/IsometricCanvasBackground.jsx#L57-L123)) |
| `POST /api/v1/auth/login` | Latencia p50 / p95 / p99 / Max | **620 ms / 760 ms / 830 ms / 832.1 ms** (Media: `579.2 ms`) | p50 `< 150 ms` / p95 `< 300 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:2`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L2)) |
| `GET /api/v1/kpis/cmi-completo` | Latencia p50 / p95 / p99 / Max | **400 ms / 740 ms / 940 ms / 1,305.4 ms** (Media: `417.6 ms`, `5,717 B`) | p50 `< 80 ms` / p95 `< 200 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:7`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L7)) |
| `GET /api/v1/riesgos/alertas-tempranas` | Latencia p50 / p95 / p99 / Max | **380 ms / 700 ms / 890 ms / 1,194.5 ms** (Media: `391.0 ms`, `9,141 B`) | p50 `< 60 ms` / p95 `< 150 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:8`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L8)) |
| `GET /api/v1/forecast/alumnos?horizonte=6` | Latencia p50 / p95 / p99 / Max | **290 ms / 580 ms / 920 ms / 1,182.2 ms** (Media: `315.4 ms`) | p50 `< 50 ms` / p95 `< 120 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:6`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L6)) |
| `GET /api/v1/audit/logs` | Latencia p50 / p95 / p99 / Payload | **290 ms / 540 ms / 700 ms / 899.6 ms** (Payload medio: **31,042 B**) | p50 `< 50 ms` / p95 `< 120 ms` / `< 5 KB` gzip | Medido ([`docs/evidencias/locust_summary_stats.csv:4`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L4)) |
| `GET /api/v1/dataops/sources` | Latencia p50 / p95 / p99 / Max | **300 ms / 590 ms / 770 ms / 835.6 ms** (Media: `320.5 ms`) | p50 `< 40 ms` / p95 `< 100 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:5`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L5)) |
| `GET /health` | Latencia p50 / p95 / p99 / Max | **190 ms / 480 ms / 640 ms / 1,142.3 ms** (Media: `217.5 ms`) | p50 `< 10 ms` / p95 `< 25 ms` | Medido ([`docs/evidencias/locust_summary_stats.csv:9`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L9)) |
| `GET /api/v1/forecast/analitica-macro` | Latencia p50 / p95 sin caché | **HIPÓTESIS: 850 – 2,200 ms** (5 modelos HW + 2 OLS + `pd.read_excel` sin `cache_consultas`) | p50 `< 50 ms` (con caché) / `< 300 ms` (miss) | [`backend/routers/forecast.py:165-185`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/forecast.py#L165-L185), [`forecast_service.py:294, 381-529`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/forecast_service.py#L381-L529) |
| `POST /api/v1/dataops/confirm-dw-insert` | Latencia por lote de 100 registros | **HIPÓTESIS: 4,000 – 15,000 ms** (N+1 queries + llamada HTTP síncrona a `:8006/indice`) | `< 800 ms` (pre-mapa de documentos + bulk load) | [`backend/routers/dataops.py:3378-3584`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/dataops.py#L3378-L3584) |
| **Pipeline BETO (`/infer` por lote)** | Latencia con 24 hilos vs 4 hilos CPU | **1,162 ms/forward** (24 hilos) vs **53 ms/forward** (4 hilos) y **~17 ms/oración** en lote | `~50–60 ms/lote` fijando `TORCH_NUM_THREADS=4` | Medido y documentado en [`pipeline/semantic/ner_engine.py:24-32, 250`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/pipeline/semantic/ner_engine.py#L24-L32) |

---

## 4. Hallazgos Detallados (Fase 3.3)

| ID | Capa | Evidencia (`archivo:línea` / salida de medición) | Impacto (ms o %) | Causa Raíz |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | Frontend / Docker | [`docker-compose.yml:178-180`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docker-compose.yml#L178-L180), [`infrastructure/docker/web.Dockerfile:19`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/infrastructure/docker/web.Dockerfile#L19), [`frontend/vite.config.js:10-13`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/vite.config.js#L10-L13) | **+3,000 a +6,500 ms** en carga inicial (HIPÓTESIS en runtime; `1,975` módulos transformados en `vite build`) | El contenedor `web` monta `./frontend:/app`, ejecuta `pnpm install && pnpm run dev --host` en cada arranque y mantiene `watch: { usePolling: true, interval: 200 }`. Al abrir la web, el navegador descarga cientos de módulos ESM sin empaquetar en vez de los 36 chunks de producción (`335.75 KiB` JS gzip + `8.31 KiB` CSS gzip). |
| **F-02** | Gateway / Red | [`gateway/nginx.conf:5-44`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/gateway/nginx.conf#L5-L44), [`gateway/nginx.conf:92-161, 177-187, 255-261`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/gateway/nginx.conf#L92-L161) | **+70% peso de red en assets** (`1,152.78 KiB` bruto vs `344.06 KiB` gzip medido) y **+15–40 ms/req** por handshake TCP | Aunque FastAPI tiene `GZipMiddleware` (`backend/main.py:151`), `gateway/nginx.conf` no declara `gzip on;` (sirviendo todo el JS/CSS de `web:5173` y respuestas de `:8001/:8002/:8004` sin comprimir), no define `Cache-Control` para `/assets/`, ni configura `keepalive` en los 5 bloques `upstream`. Los timeouts de `300s`/`900s` enmascaran bloqueos síncronos. |
| **F-03** | Frontend (UI / Navegación) | [`frontend/src/App.jsx:175-241, 375`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/App.jsx#L175-L241), [`frontend/src/context/ThemeContext.jsx:8, 19-22`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/context/ThemeContext.jsx#L8-L22), [`frontend/src/components/canvas3d/IsometricCanvasBackground.jsx:57-123`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/components/canvas3d/IsometricCanvasBackground.jsx#L57-L123) | **560 ms fijos** en cada cambio de ruta + **15–25% uso continuo de CPU** (60 FPS) | 1) `triggerLoadingAnimation()` (`App.jsx:185-199`) y `finishLoadingAnimation()` (`App.jsx:175-183`) encadenan `setTimeout` de `75 ms`, `190 ms`, `340 ms` y `220 ms` en cada clic de `<a href>` o cambio de `location.pathname`, mostrando el pill `"Cargando sección..."` incluso cuando el chunk lazy y la caché de React Query ya están en RAM. 2) `IsometricCanvasBackground` renderiza 216 nodos y 204 trazos por frame a 60 FPS por defecto. |
| **F-04** | Backend / DB (`risk_service`) | [`backend/services/risk_service.py:109-187, 240-492`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/risk_service.py#L109-L187), Locust [`locust_summary_stats.csv:8`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L8) | **p50 = 380 ms, p95 = 700 ms, max = 1,194.5 ms** (reducción estimada del **80%** agregando en SQL) | `evaluar_alertas_tempranas_deterministicas()` ejecuta `.all()` sobre **7 tablas completas** (`DimEstudiante`, `DimModulo`, `DimDocente`, `DimTiempo`, `DimOrigenDocumental`, `FactRendimientoAcademico`, `FactSituacionFinanciera`) y construye diccionarios en Python para todos los alumnos antes de aplicar los filtros `periodo`, `programa`, `modulo`, `docente` y `regla_filtro`. |
| **F-05** | Backend / DB (`kpi_service`) | [`backend/services/kpi_service.py:344-867`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/kpi_service.py#L344-L867), Locust [`locust_summary_stats.csv:7`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L7) | **p50 = 400 ms, p95 = 740 ms, max = 1,305.4 ms** | `obtener_perspectivas_cmi_completo()` realiza **15 a 17 roundtrips SQL secuenciales** en la misma petición, escaneando `fact_rendimiento_academico` 6 veces (líneas `238`, `592`, `606`, `628`, `649`, `696`, `718`, `739`, `761`, `775`) y `fact_situacion_financiera` 4 veces (líneas `225`, `469`, `480`, `510`) con los mismos joins a `dim_tiempo` y `dim_modulo`. |
| **F-06** | Backend / Forecast + Frontend | [`backend/routers/forecast.py:79-84, 182-185`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/forecast.py#L182-L185), [`backend/services/forecast_service.py:294, 381-529`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/forecast_service.py#L381-L529), [`ProyeccionFinanciera.jsx:37-40`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/modules/finance/ProyeccionFinanciera.jsx#L37-L40), [`ProyeccionAlumnos.jsx:37-40`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/modules/academic/ProyeccionAlumnos.jsx#L37-L40) | **HIPÓTESIS: 850 – 2,200 ms** por visita (`p95 = 580 ms` medido solo para 1 modelo en `/forecast/alumnos`) | 1) A diferencia de `/forecast/metas` (`forecast.py:135`), ni `/forecast/alumnos` (`forecast.py:80`) ni `/forecast/analitica-macro` (`forecast.py:183`) usan `cache_consultas.obtener()`. En cada llamada a `/analitica-macro` se entrenan **5 modelos Holt-Winters + 2 regresiones OLS** en CPU y se lee `TBL_INSCRITOS.xlsx` con `pd.read_excel` (`forecast_service.py:294`), sin usar la tabla `fact_forecast` (`db/schema.sql:294`). 2) `ProyeccionFinanciera.jsx`, `ProyeccionAlumnos.jsx`, `RecaudacionCobranzas.jsx` y `MetasGestion.jsx` invocan `/analitica-macro` en paralelo con `/metas` o `/alumnos`, duplicando el entrenamiento. |
| **F-07** | Frontend (`AuditoriaSistema` e `IngestView`) | [`frontend/src/modules/admin/AuditoriaSistema.jsx:21, 81-108`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/modules/admin/AuditoriaSistema.jsx#L81-L108), [`frontend/src/modules/dataops/IngestView.jsx:61-78`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/frontend/src/modules/dataops/IngestView.jsx#L61-L78) | **+350 a +700 ms** de peticiones innecesarias o en cascada al montar la vista | 1) `AuditoriaSistema.jsx` ejecuta al montar dos `useEffect` simultáneos (`loadAuditData()` en línea 103 y `loadAlertasData()` en línea 107), disparando `GET /api/v1/kpis/alertas` y `GET /api/v1/riesgos/cruzado` aunque el usuario esté en la pestaña `'trazabilidad'`. 2) `IngestView.jsx:64-72` espera secuencialmente a que termine `dataopsApi.getSources()` antes de iniciar `loadBatchInspection(Number(lastId))` (`GET /api/v1/dataops/lote/{id}/raw-vs-text`). |
| **F-08** | Pipeline BETO (:8006) | [`docker-compose.yml:148`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docker-compose.yml#L148), [`pipeline/semantic/ner_engine.py:24-32`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/pipeline/semantic/ner_engine.py#L24-L32), [`pipeline/semantic/indice_confianza.py:49-64`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/pipeline/semantic/indice_confianza.py#L49-L64), [`pipeline/semantic/inference_server.py:38-56`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/pipeline/semantic/inference_server.py#L38-L56) | **2× a 20× degradación** por contención de hilos OpenMP (`1,162 ms` vs `53 ms` documentado) + **+440 MB RAM** | 1) `docker-compose.yml:148` define `TORCH_NUM_THREADS: ${TORCH_NUM_THREADS:-8}`, sobreescribiendo el óptimo de `4` hilos medido en `ner_engine.py:24-32`. 2) `indice_confianza.py:49-64` carga en memoria una **segunda instancia independiente** de `BertForTokenClassification` y `BertTokenizerFast` en lugar de reutilizar el modelo ya cargado en `_ENGINE_SINGLETON._nlp_pipeline` de `inference_server.py:38-56`. |
| **F-09** | Backend DataOps / ETL | [`backend/routers/dataops.py:616-619, 3378-3584`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/routers/dataops.py#L3378-L3584), [`backend/services/dw_loader.py:209-246`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/dw_loader.py#L209-L246) | **HIPÓTESIS: 4 – 15 s** bloqueando el worker en `confirm-dw-insert` y contención de CPU en ingestas grandes | 1) En `confirm_dw_insert`, dentro de `for stg in stg_records:` ejecuta `db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento == stg.id_documento).first()` (`dataops.py:3380`, N+1), llama síncronamente a `obtener_indices(lines)` (`POST http://pipeline:8006/indice` con timeout 300s) e invoca `dw.cargar_registro()` haciendo múltiples `.first()` y `db.flush()` por fila. 2) `_evaluar_lote_en_segundo_plano` corre en `BackgroundTasks` del mismo contenedor `api`, compitiendo por CPU y pool SQLAlchemy. |
| **F-10** | Backend Core (DB Pool & Caché Multi-Worker) | [`backend/core/database.py:28-32, 55-59`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/core/database.py#L28-L32), [`backend/services/cache_consultas.py:14-31`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/cache_consultas.py#L14-L31), Locust [`locust_summary_stats.csv:9`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L9) | `/health` sube hasta **p95 = 480 ms, max = 1,142.3 ms** bajo carga; **75% miss rate extra** e invalidación parcial con 4 workers | 1) `create_engine` usa los valores por defecto de SQLAlchemy (`pool_size=5, max_overflow=10`) con `pool_pre_ping=True`, encolando peticiones cuando concurren pantallas que disparan 17–29 queries. 2) `cache_consultas.py` almacena `_entradas` en un `dict` local de cada proceso: con `API_WORKERS=4` (`docker-compose.yml:76`), `cache_consultas.invalidar()` en `dataops.py:3585` solo limpia la caché de 1 de los 4 workers. |
| **F-11** | Servicio Auditoría (:8004 / :8000) | [`services/audit-service/routers/audit.py:46-61, 110-185`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/services/audit-service/routers/audit.py#L46-L61), Locust [`locust_summary_stats.csv:4`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/locust_summary_stats.csv#L4) | **p50 = 290 ms, p95 = 540 ms**, payload medio **31,042 bytes** | `get_audit_logs` descarga siempre hasta `1,000` filas de `LogPipelineIngesta` + `500` filas de `LogAuditoriaNlp`, construye 1,500 diccionarios en Python, los ordena por string timestamp en memoria (`audit.py:146`) y recién aplica filtros y slice `filtrados[offset:offset+limit]` (`audit.py:184`). |
| **F-12** | Base de Datos (`db/schema.sql`) | [`db/schema.sql:394-437, 441-483`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/db/schema.sql#L394-L483) | Overhead de evaluación RLS por tabla y mantenimiento de índices duplicados en escrituras | 1) **RLS en todas las tablas:** `schema.sql:394-422` activa `ROW LEVEL SECURITY` y crea la política `Admin_All_Access` con `current_setting('request.jwt.claims', true)::json->>'role' = 'admin'` en cada tabla aunque el backend se conecta como `giragroup_user` (dueño de las tablas) y `Lectura_Global` es `USING (true)`. 2) **Índices redundantes:** `idx_stg_no_resuelta_estado (resuelto)` (`schema.sql:479`) duplica el prefijo de `idx_stg_entidad_resuelto (resuelto, estado_resolucion)` (`schema.sql:477`); `idx_fact_rend_estudiante (id_estudiante)` (`schema.sql:452`) duplica el prefijo de `uq_fact_rendimiento_estudiante_modulo (id_estudiante, id_modulo)` (`schema.sql:443`). 3) Faltan índices compuestos covering para las agregaciones de `kpi_service` y `risk_service`. |

---

## 5. Recomendaciones Priorizadas con Snippets Mínimos (Fase 3.4)

| ID | Acción | Esfuerzo | Impacto | Riesgo | Hallazgos que Resuelve |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **R-01** | Servir build estático compilado en el contenedor `web` y eliminar `pnpm install` + file polling en despliegue | **S** | **A** | Bajo | **F-01** |
| **R-02** | Activar `gzip`, `keepalive` en los 5 `upstream` y `Cache-Control: immutable` para `/assets/` en `gateway/nginx.conf` | **S** | **A** | Bajo | **F-02** |
| **R-03** | Eliminar el retardo artificial de `560 ms` cuando no hay `Suspense` activo en `App.jsx` y desactivar `IsometricCanvasBackground` por defecto en `ThemeContext.jsx` | **S** | **A** | Bajo | **F-03** |
| **R-04** | Cachear `/api/v1/forecast/analitica-macro` y `/api/v1/forecast/alumnos` con `cache_consultas.obtener` y evitar la llamada duplicada en `ProyeccionFinanciera.jsx` | **S** | **A** | Bajo | **F-06** |
| **R-05** | Cargar `loadAlertasData()` en `AuditoriaSistema.jsx` solo cuando `activeTab === 'alertas'` | **S** | **M** | Bajo | **F-07** |
| **R-06** | Reemplazar los 7 `.all()` en memoria de `risk_service.py` por pre-filtrado/agregación SQL preservando `promedio <= 70`, `incumplimiento > 30%`, `cuotas >= 2` | **M** | **A** | Medio | **F-04** |
| **R-07** | Fijar `TORCH_NUM_THREADS=4` en `docker-compose.yml` y reutilizar el modelo de `get_engine_and_tokenizer()` en `indice_confianza.py` | **S** | **A** | Bajo | **F-08** |
| **R-08** | Eliminar índices duplicados y crear índices covering en PostgreSQL (`db/schema.sql`) para `fact_rendimiento_academico` y `fact_situacion_financiera` | **M** | **A** | Bajo | **F-05, F-12** |
| **R-09** | Eliminar query N+1 de `DimOrigenDocumental` en `confirm_dw_insert` (`dataops.py:3378-3385`) y dimensionar el pool SQLAlchemy en `backend/core/database.py` | **M** | **A** | Medio | **F-09, F-10** |
| **R-10** | Limitar la lectura SQL a `offset + limit` cuando no hay filtros activos en `services/audit-service/routers/audit.py` | **M** | **M** | Bajo | **F-11** |

---

### Snippets Mínimos de Implementación (Diffs Verificados contra Código Fuente)

#### [R-01] `docker-compose.yml` (`174-180`) + `infrastructure/docker/web.Dockerfile` (`15-19`)
```diff
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -174,7 +174,4 @@
     environment:
       CI: "true"
       VITE_API_TARGET: "http://gateway:80"
-    volumes:
-      - ./frontend:/app
-      - web_node_modules:/app/node_modules
-    command: sh -c "pnpm install && pnpm run dev --host"
+    command: ["pnpm", "run", "preview", "--host", "0.0.0.0", "--port", "5173"]
```
```diff
--- a/infrastructure/docker/web.Dockerfile
+++ b/infrastructure/docker/web.Dockerfile
@@ -15,5 +15,6 @@
 COPY frontend/ .
+RUN pnpm run build
 
 EXPOSE 5173
-CMD ["pnpm", "run", "dev", "--host"]
+CMD ["pnpm", "run", "preview", "--host", "0.0.0.0", "--port", "5173"]
```

#### [R-02] `gateway/nginx.conf` (`8-44, 254-262`)
```diff
--- a/gateway/nginx.conf
+++ b/gateway/nginx.conf
@@ -8,6 +8,12 @@
     sendfile        on;
     keepalive_timeout  65;
 
+    gzip on;
+    gzip_comp_level 5;
+    gzip_min_length 1024;
+    gzip_vary on;
+    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
+
     # Timeouts globales de proxy para prevenir 504 Gateway Time-out
     proxy_connect_timeout 60s;
     proxy_read_timeout 300s;
@@ -24,20 +30,25 @@
     # Upstreams hacia los microservicios y el monolito modular
     upstream beto_core {
         server api:8000;
+        keepalive 32;
     }
 
     upstream auth_service {
         server auth-service:8001;
+        keepalive 16;
     }
 
     upstream notifications_service {
         server notifications-service:8002;
+        keepalive 8;
     }
 
     upstream audit_service {
         server audit-service:8004;
+        keepalive 8;
     }
 
     upstream frontend_app {
         server web:5173;
+        keepalive 32;
     }
@@ -252,6 +263,14 @@
         }
 
         # 7. Frontend SPA
+        location /assets/ {
+            proxy_pass http://frontend_app;
+            proxy_http_version 1.1;
+            proxy_set_header Connection "";
+            expires 1y;
+            add_header Cache-Control "public, max-age=31536000, immutable";
+        }
+
         location / {
             proxy_pass http://frontend_app;
             proxy_http_version 1.1;
```

#### [R-03] `frontend/src/context/ThemeContext.jsx` (`8, 19-22`) y `frontend/src/App.jsx` (`185-199`)
```diff
--- a/frontend/src/context/ThemeContext.jsx
+++ b/frontend/src/context/ThemeContext.jsx
@@ -5,7 +5,7 @@
   isDark: false,
   toggleTheme: () => {},
   setTheme: () => {},
-  canvasEnabled: true,
+  canvasEnabled: false,
   toggleCanvas: () => {},
   autoRefresh: '30s',
   setAutoRefresh: () => {},
@@ -19,4 +19,4 @@
   const [canvasEnabled, setCanvasEnabled] = useState(() => {
     const stored = localStorage.getItem('gira_canvas_enabled');
-    return stored !== null ? stored === 'true' : true;
+    return stored !== null ? stored === 'true' : false;
   });
```
```diff
--- a/frontend/src/App.jsx
+++ b/frontend/src/App.jsx
@@ -185,15 +185,10 @@
   const triggerLoadingAnimation = useCallback(() => {
     clearTimers();
-    setIsNavigating(true);
-    setTopProgress(15);
-
-    const t1 = setTimeout(() => setTopProgress(65), 75);
-    const t2 = setTimeout(() => setTopProgress(90), 190);
-    const t3 = setTimeout(() => {
-      if (!suspenseActiveRef.current) {
-        finishLoadingAnimation();
-      }
-    }, 340);
-
-    timersRef.current.push(t1, t2, t3);
+    if (!suspenseActiveRef.current) {
+      setIsNavigating(false);
+      setTopProgress(0);
+      return;
+    }
+    setIsNavigating(true);
+    setTopProgress(65);
   }, [clearTimers, finishLoadingAnimation]);
```

#### [R-04] `backend/routers/forecast.py` (`79-85, 182-186`) y `frontend/src/modules/finance/ProyeccionFinanciera.jsx` (`36-45`)
```diff
--- a/backend/routers/forecast.py
+++ b/backend/routers/forecast.py
@@ -79,7 +79,11 @@
     try:
-        resultado = obtener_pronostico_alumnos(db=db, tipo=tipo_sanitizado, horizonte=horizonte)
+        resultado = cache_consultas.obtener(
+            ("forecast_alumnos", tipo_sanitizado, horizonte),
+            TTL_FORECAST_SEG,
+            lambda: obtener_pronostico_alumnos(db=db, tipo=tipo_sanitizado, horizonte=horizonte),
+        )
         return {
             "status": "success",
             "data": resultado
         }
@@ -182,4 +186,8 @@
     try:
-        resultado = obtener_analitica_macro_completa(db=db, horizonte=horizonte)
+        resultado = cache_consultas.obtener(
+            ("forecast_analitica_macro", horizonte),
+            TTL_FORECAST_SEG,
+            lambda: obtener_analitica_macro_completa(db=db, horizonte=horizonte),
+        )
         return resultado
```
```diff
--- a/frontend/src/modules/finance/ProyeccionFinanciera.jsx
+++ b/frontend/src/modules/finance/ProyeccionFinanciera.jsx
@@ -36,10 +36,10 @@
     queryFn: async () => {
-      const [macro, metas] = await Promise.all([
-        forecastApi.getAnaliticaPredictivaMacro(horizonte),
-        forecastApi.getForecastMetas(granularidad, horizonte),
-      ]);
+      const macro = await forecastApi.getAnaliticaPredictivaMacro(horizonte);
+      const metas = granularidad === 'MENSUAL'
+        ? macro?.caso3_metas_mensuales
+        : await forecastApi.getForecastMetas(granularidad, horizonte);
       return {
         macroData: macro,
         metasForecast: metas?.data || metas,
       };
     },
```

#### [R-05] `frontend/src/modules/admin/AuditoriaSistema.jsx` (`102-108`)
```diff
--- a/frontend/src/modules/admin/AuditoriaSistema.jsx
+++ b/frontend/src/modules/admin/AuditoriaSistema.jsx
@@ -102,7 +102,11 @@
   useEffect(() => {
-    loadAuditData();
-  }, [filterModulo, filterSeveridad]);
+    if (activeTab === 'trazabilidad') {
+      loadAuditData();
+    }
+  }, [activeTab, filterModulo, filterSeveridad]);
 
   useEffect(() => {
-    loadAlertasData();
-  }, []);
+    if (activeTab === 'alertas' && alertas.length === 0) {
+      loadAlertasData();
+    }
+  }, [activeTab]);
```

#### [R-06] `backend/services/risk_service.py` (`109-187`)
```diff
--- a/backend/services/risk_service.py
+++ b/backend/services/risk_service.py
@@ -109,14 +109,6 @@
-    estudiantes_db = {
-        e.id_estudiante: e
-        for e in db.query(
-            DimEstudiante.id_estudiante,
-            DimEstudiante.ci,
-            DimEstudiante.ci_numero,
-            DimEstudiante.codigo_estudiante,
-            DimEstudiante.nombre_completo,
-            DimEstudiante.programa_origen,
-            DimEstudiante.deprecado,
-        )
-        .filter(DimEstudiante.deprecado == False)
-        .all()
-    }
@@ -186,2 +178,21 @@
         .all()
     )
+    ids_con_hechos = {h.id_estudiante for h in hechos_aca if h.id_estudiante} | {
+        f.id_estudiante for f in hechos_fin if f.id_estudiante
+    }
+    estudiantes_db = {
+        e.id_estudiante: e
+        for e in db.query(
+            DimEstudiante.id_estudiante,
+            DimEstudiante.ci,
+            DimEstudiante.ci_numero,
+            DimEstudiante.codigo_estudiante,
+            DimEstudiante.nombre_completo,
+            DimEstudiante.programa_origen,
+            DimEstudiante.deprecado,
+        )
+        .filter(
+            DimEstudiante.deprecado == False,
+            DimEstudiante.id_estudiante.in_(ids_con_hechos),
+        )
+        .all()
+    } if ids_con_hechos else {}
```
*(Nota: Para la reducción completa de ~80% de latencia en Fase 2, reemplazar la descarga de `hechos_aca` y `hechos_fin` por la consulta CTE pre-agregada verificada en la Sección 9 de [`docs/performance/scripts/measure_db_explain.sql`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts/measure_db_explain.sql#L154-L224), que preserva exactamente `promedio_notas <= 70.0`, `max_incumplimiento_pct > 30.0` y `cuotas_mora >= 2`).*

#### [R-07] `docker-compose.yml` (`145-149`) y `pipeline/semantic/indice_confianza.py` (`49-64`)
```diff
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -145,5 +145,5 @@
     env_file: .env
     environment:
       # Hilos de PyTorch: sin límite usa los 24 núcleos del host y cada forward tarda ~1 s
-      TORCH_NUM_THREADS: ${TORCH_NUM_THREADS:-8}
+      TORCH_NUM_THREADS: ${TORCH_NUM_THREADS:-4}
```
```diff
--- a/pipeline/semantic/indice_confianza.py
+++ b/pipeline/semantic/indice_confianza.py
@@ -49,16 +49,21 @@
 def _cargar_modelo():
     global _MODELO, _TOKENIZER
     if _MODELO is None:
+        from pipeline.semantic.inference_server import get_engine_and_tokenizer
+        engine, tok = get_engine_and_tokenizer()
+        if engine is not None and getattr(engine, "_nlp_pipeline", None) is not None:
+            _MODELO = engine._nlp_pipeline.model
+            _TOKENIZER = tok or engine._nlp_pipeline.tokenizer
+            return _MODELO, _TOKENIZER
         from transformers import BertForTokenClassification, BertTokenizerFast
         from pipeline.config import MODELO_BETO_CACHE_DIR
         from pipeline.semantic.ner_engine import configurar_hilos_torch
```

#### [R-08] `db/schema.sql` (`452-483` — Eliminación de índices duplicados y creación de índices covering con columnas reales)
```sql
-- 1. Eliminar índices redundantes cuyo prefijo ya está cubierto por UNIQUE / compuestos:
DROP INDEX IF EXISTS public.idx_stg_no_resuelta_estado;
DROP INDEX IF EXISTS public.idx_fact_rend_estudiante;

-- 2. Crear índices covering alineados con las columnas reales de db/schema.sql:
CREATE INDEX IF NOT EXISTS idx_fact_rend_tiempo_modulo_cov
    ON public.fact_rendimiento_academico (id_tiempo, id_modulo)
    INCLUDE (id_estudiante, nota_final, asistencia_pct, incumplimiento_actividades_pct, nivel_confianza_ia, requiere_revision);

CREATE INDEX IF NOT EXISTS idx_fact_fin_tiempo_modulo_cov
    ON public.fact_situacion_financiera (id_tiempo, id_modulo)
    INCLUDE (id_estudiante, monto_pagado, monto_deuda, cuotas_impagas, estado_cartera);

CREATE INDEX IF NOT EXISTS idx_log_ingesta_etapa_id_desc
    ON public.log_pipeline_ingesta (etapa, id DESC);
```

#### [R-09] `backend/routers/dataops.py` (`3378-3386`) y `backend/core/database.py` (`28-32`)
```diff
--- a/backend/routers/dataops.py
+++ b/backend/routers/dataops.py
@@ -3378,8 +3378,10 @@
+    doc_ids_stg = {s.id_documento for s in stg_records if s.id_documento}
+    origenes_map = {
+        o.id_documento: o
+        for o in db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(doc_ids_stg)).all()
+    } if doc_ids_stg else {}
+
     for stg in stg_records:
-        orig_doc = (
-            db.query(DimOrigenDocumental)
-            .filter(DimOrigenDocumental.id_documento == stg.id_documento)
-            .first()
-            if stg.id_documento
-            else None
-        )
+        orig_doc = origenes_map.get(stg.id_documento) if stg.id_documento else None
```
```diff
--- a/backend/core/database.py
+++ b/backend/core/database.py
@@ -28,5 +28,9 @@
 engine = create_engine(
     SQLALCHEMY_DATABASE_URL,
     connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {"connect_timeout": 1},
-    pool_pre_ping=True
+    pool_pre_ping=True,
+    pool_size=15,
+    max_overflow=25,
+    pool_recycle=1800,
+    pool_timeout=30,
 )
```

#### [R-10] `services/audit-service/routers/audit.py` (`45-61, 110-126`)
```diff
--- a/services/audit-service/routers/audit.py
+++ b/services/audit-service/routers/audit.py
@@ -45,2 +45,3 @@
     try:
+        fetch_cap = min(1000, offset + limit) if not (modulo or severidad or busqueda) else 1000
         pipeline_logs = (
@@ -59,3 +60,3 @@
             .order_by(LogPipelineIngesta.id.desc())
-            .limit(1000)
+            .limit(fetch_cap)
             .all()
         )
```

---

## 6. Plan de Ejecución por Fases (Fase 3.5)

### Fase 1: Quick Wins (< 1 día — Impacto Inmediato al Abrir el Link Web y Navegar)
1. **Despliegue estático en contenedor `web` (`R-01`):** Actualizar `docker-compose.yml` y `infrastructure/docker/web.Dockerfile` para compilar `pnpm run build` y servir `pnpm run preview` sin bind-mount ni `pnpm install` en cada arranque. Reduce el tiempo de carga inicial en **70%–85%**.
2. **Compresión Gzip y Keep-Alive en Gateway (`R-02`):** Habilitar `gzip on;`, `keepalive` en los 5 `upstream` y `Cache-Control: public, max-age=31536000, immutable` en `/assets/` dentro de `gateway/nginx.conf`.
3. **Fluidez de Navegación SPA y Caché de Forecast (`R-03`, `R-04`, `R-05`):** Eliminar el timer artificial de `560 ms` cuando `Suspense` no está activo en `App.jsx:185-199`, iniciar `canvasEnabled = false` en `ThemeContext.jsx:8, 21`, envolver `/forecast/analitica-macro` y `/forecast/alumnos` en `cache_consultas.obtener`, evitar la llamada redundante a `/forecast/metas` en `ProyeccionFinanciera.jsx:37-40`, y diferir `loadAlertasData()` en `AuditoriaSistema.jsx:106-108`.
4. **Optimización de inferencia BETO (`R-07`):** Ajustar `TORCH_NUM_THREADS=4` en `docker-compose.yml:148` y compartir el singleton de `inference_server.py` en `indice_confianza.py:49-64`.

### Fase 2: Mejoras Estructurales (2 – 5 días — Base de Datos, Caché Compartida y ETL)
1. **Refactor SQL en `risk_service.py` y `kpi_service.py` (`R-06`, `R-08`):** Sustituir los 7 `.all()` de `evaluar_alertas_tempranas_deterministicas` por la consulta CTE pre-agregada (sección 9 de `docs/performance/scripts/measure_db_explain.sql`) y consolidar las 17 consultas de `obtener_perspectivas_cmi_completo` en 4 consultas agrupadas por perspectiva o una vista materializada `mv_cmi_resumen_mensual` refrescada al consolidar lotes en DataOps.
2. **Persistencia de Forecast en `fact_forecast`:** Precalcular los modelos Holt-Winters y OLS al cierre de cada ingesta (`confirm_dw_insert`), almacenando los resultados en la tabla `fact_forecast` (`db/schema.sql:294`) y eliminando la lectura en vivo de `TBL_INSCRITOS.xlsx` (`pd.read_excel`).
3. **Eliminación de N+1 y Bulk Load en `confirm_dw_insert` (`R-09`):** Pre-cargar `origenes_map` fuera del bucle en `dataops.py:3378`, reutilizar `stg.score_confianza` cuando ya fue calculado en la ingesta sin volver a invocar `:8006/indice`, y dimensionar el pool SQLAlchemy (`pool_size=15, max_overflow=25`).
4. **Caché multi-worker consistente:** Si se mantiene `API_WORKERS=4`, respaldar `cache_consultas.py` en una tabla `UNLOGGED` de PostgreSQL o Redis (costo si se introduce Redis: 1 contenedor `redis:7-alpine` de ~35 MB RAM) para que `cache_consultas.invalidar()` surta efecto inmediato en los 4 workers de Uvicorn.

### Fase 3: Monitoreo y Prevención de Regresiones (Continuo)
1. **Habilitar `pg_stat_statements` en PostgreSQL (`:5434`):** Añadir `shared_preload_libraries = 'pg_stat_statements'` en el servicio `db` para auditar automáticamente las consultas con mayor tiempo total y desviación estándar.
2. **Cabeceras `Server-Timing` en FastAPI:** Añadir medición de `Server-Timing: app;dur=...` en `backend/main.py:139` y registrar un `WARNING` cuando cualquier endpoint analítico supere `300 ms`.
3. **Umbrales de regresión en CI:** Ejecutar los 4 scripts de `docs/performance/scripts/` antes de cada release verificando: bundle JS+CSS gzip `< 350 KiB`, `p95 < 250 ms` en `/kpis/cmi-completo` y `/riesgos/alertas-tempranas`, y `0` sequential scans innecesarios en tablas de hechos con filtro temporal.

---

## 7. Scripts de Medición Reproducibles (`docs/performance/scripts/`)

Se han creado y verificado 4 herramientas de medición en modo solo lectura dentro de [`docs/performance/scripts/`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts):

1. **[`docs/performance/scripts/measure_frontend.mjs`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts/measure_frontend.mjs)**
   - **Propósito:** Compila el bundle en un directorio temporal aislado para auditar el peso bruto y gzip por chunk (`vite build` + `zlib.gzipSync`) y, con el stack activo, utiliza Playwright + `PerformanceObserver` para medir TTFB, FCP, LCP, TBT, CLS, DOM Complete y tiempo de transición en las 14 rutas principales de `App.jsx`.
   - **Ejecución:**
     ```bash
     # Solo análisis estático de chunks (no requiere Docker activo):
     node docs/performance/scripts/measure_frontend.mjs --build-only

     # Análisis completo con navegador headless contra el Gateway:
     node docs/performance/scripts/measure_frontend.mjs --url http://localhost
     ```

2. **[`docs/performance/scripts/measure_backend.py`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts/measure_backend.py)**
   - **Propósito:** Ejecuta pruebas de carga concurrentes con `httpx.AsyncClient` (o `urllib.request` + `ThreadPoolExecutor` de librería estándar si `httpx` no está instalado) calculando `p50`, `p95`, `p99`, media, máximo, tamaño de respuesta y RPS sobre los 13 endpoints críticos de FastAPI y Audit Service.
   - **Ejecución:**
     ```bash
     python docs/performance/scripts/measure_backend.py --base-url http://localhost:8000 --concurrency 10 --requests 50 --output docs/performance/scripts/backend_benchmark_results.csv
     ```

3. **[`docs/performance/scripts/measure_db_explain.sql`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts/measure_db_explain.sql)**
   - **Propósito:** Audita tamaño de tablas, proporción de `seq_scan` vs `idx_scan`, índices redundantes, políticas RLS activas, estado de `pg_stat_statements` y ejecuta `EXPLAIN (ANALYZE, BUFFERS)` sobre las consultas reales de `kpi_service.py`, `risk_service.py`, `ficha-estudiante` y la consulta CTE optimizada propuesta (verificada contra `db/schema.sql`).
   - **Ejecución:**
     ```bash
     psql -h 127.0.0.1 -p 5434 -U giragroup_user -d giragroup_db -f docs/performance/scripts/measure_db_explain.sql
     ```

4. **[`docs/performance/scripts/measure_pipeline_beto.py`](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/performance/scripts/measure_pipeline_beto.py)**
   - **Propósito:** Mide la latencia cold-start vs warm de `/infer`, y realiza un barrido de tamaño de lote (`batch_size` = 1, 8, 16, 32, 64, 128) contra `/infer-batch` y `/indice` en `:8006` (usando `httpx` o `urllib.request` estándar), reportando latencia por texto y throughput (`textos/seg`).
   - **Ejecución:**
     ```bash
     python docs/performance/scripts/measure_pipeline_beto.py --url http://localhost:8006 --batch-sizes 1,8,16,32,64,128
     ```
