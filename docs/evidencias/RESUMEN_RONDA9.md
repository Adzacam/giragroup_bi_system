# Ronda 9 — frontend, Power BI, Docker y E2E con la UI real (cifras de ejecuciones reales)

## Tabla única de cifras
| Cifra | Valor | Evidencia |
|---|---|---|
| Endpoints del backend (OpenAPI de la API) / llamadas distintas del front | 95 / 88 | auditoria_endpoints_front.json |
| Llamadas del front que coinciden (método + ruta) | 88 de 88 (77 en la API; 11 de auth/notifications-service tras el gateway) | auditoria_endpoints_front.md |
| Servicios levantados tras `docker compose build` | 9 de 9 (healthchecks de db y catalog_db `healthy`; /health de api, auth, notifications, audit y pipeline responden; gateway y web 200) | ejecución |
| Versión del informe Power BI registrada | v2 vigente (171.878 bytes, sha256 ba417cac…); v1 queda como no vigente | powerbi_informe_version |
| E2E: login (con OTP) | 7,5 s | e2e/tiempos_ui.json |
| E2E: seleccionar 10 archivos / procesar el lote hasta pre-etiquetado | 1,5 s / 8,7 s | idem |
| E2E: análisis BETO + consolidación al DW (UI, en segundo plano) | 612,8 s | idem |
| E2E: casos y grupos al abrir la bandeja del lote | 185 casos en 12 grupos (3 de ellos sembrados en el clon para el diálogo de estado) | idem |
| E2E: grupos aprobados desde la UI | 16 (12 al abrir, más 4 que aparecen al resolver otros); total 5,87 s, mediana 0,26 s, máximo 1,16 s | idem, tiempo_klm.json |
| E2E: grupo "Mapear a estado canónico" (3 casos) | 1,26 s (incluye abrir el diálogo y escribir el estado) | tiempo_mapeo_ui.json |
| E2E: CMI actualizado | 0,42 s | idem |
| pytest | 464 passed, 0 failed, 11 skipped, 7 xfailed (ronda 8: 463) | pytest_junit.xml |
| Cobertura global / dw_loader / bandeja_grupos | 60,7 % (8.041 de 13.249 líneas) / 44,5 % / 95,3 % | cobertura.json, pytest_por_suite_y_cobertura.json |
| `npm run build` del frontend | sin errores; sin pruebas propias del front | ejecución |

## 1. Auditoría de endpoints
`scripts/auditoria_endpoints_front.py` compara las llamadas de `frontend/src/api` con `openapi_actual.json` y genera la tabla (endpoint, ¿lo usa el front?, ¿coincide?, pantalla). Los 11 endpoints de auth, usuarios y notificaciones no están en el OpenAPI de la API: los sirven auth-service y notifications-service detrás del gateway (comprobado en sus propios `/openapi.json`). Del backend, 18 endpoints no los usa el front; entre ellos `PATCH .../resolve`, `lock` y `unlock` de la bandeja. La tabla se generó después de la tarea 2, por eso ya marca como usados los endpoints de grupos.

## 2–4. Bandeja por grupos, etiquetas y fk_estado (UI)
- `GruposBandeja.jsx`: casos agrupados con motivo, valor normalizado y n de casos; "Aprobar grupo" (APROBAR), diálogo "Mapear a estado canónico" (MAPEAR_ESTADO) y diálogo "Corregir fecha" (CORREGIR_FECHA); los grupos sin acción de grupo (MANUAL) llevan a la vista "Caso por caso", que se conserva como alternativa.
- Contador: el `un_clic_total` del servidor cuenta solo la página cargada; la vista de grupos muestra "casos aprobables en bloque" calculado sobre todos los grupos (todos los que no son MANUAL) y el botón de la vista individual dice "(N en la cola cargada)".
- `GET /review-tray/grupos` acepta `id_lote` y devuelve `doc_ids`, y el front lo reenvía al aprobar, para que la bandeja trabaje solo con el lote activo (cambio aditivo; hallado en el E2E: sin él la bandeja mostraba también el remanente histórico).
- Motivos con texto legible (`motivosBandeja.js`), fuente de resolución por entidad y estado de vínculo en el detalle del caso (el item expone `entidades` y `fk_estado`), leyenda A/B/C en la bandeja. No existían filtros por fk_estado en la UI.

## 5. CMI web
KPI-10 se llama "Confianza media de extracción" (migración 013; `bi.ref_kpi` es la fuente del nombre en la web y en Power BI). La ficha docente muestra "Sin vinculación de docente en la fuente (limitación)" en lugar de "Sin evaluaciones", porque `fact_evaluacion_docente` no tiene docente (0 de 14.234 filas con `id_docente`).

## 6. Power BI
Límites de esta máquina: Power BI Desktop no está instalado, y la lectura del `DataModel` comprimido con `pbixray` está bloqueada por la política de control de aplicaciones de Windows, así que no pude abrir el modelo ni ejecutar "Actualizar". Lo comprobado: (a) la capa de informe del `.pbix` (visuales y páginas) usa solo las tablas Gestiones, Perspectivas, Scorecard, IndicePerspectiva, MetasMensual, CarteraEstado, RiesgoEstudiante y DataOpsDocumento (`powerbi_uso_tablas_columnas.json`); (b) esas consultas leen únicamente vistas del esquema `bi` (`powerbi/cmi/01_power_query.pq`), las 8 vistas existen y devuelven filas en el DW; (c) ninguna referencia a `cat_docente`, `cat_alias*`, `id_cat_docente` ni al nombre antiguo del KPI-10 en el informe, las consultas ni las vistas; (d) el nombre del KPI-10 llega por `Scorecard[nombre]`, así que cambia al actualizar. El `.pbix` de trabajo (modificado el 2026-11-09, no era el vigente) se registró como v2 con nota. **Pendiente para ti: abrir v2 en Power BI Desktop y pulsar "Actualizar" para confirmar que termina sin errores.**

## 7. Docker
`docker compose build` terminó sin errores; los 9 servicios arrancaron. Hubo que reconstruir `web` una segunda vez: la imagen lleva el `src` copiado y la primera construcción no tenía el cambio de `id_lote`.

## 8. E2E con Playwright (UI real, clon del DW)
`e2e/ciclo_ui.mjs` y `e2e/mapeo_ui.mjs`: login con 2FA (OTP leído del log del auth-service con un usuario de prueba creado solo en el clon), carga de los 10 archivos del ciclo, lectura BETO, consolidación al DW, bandeja por grupos, aprobación de todos los grupos y CMI. Capturas en `docs/evidencias/e2e/` (bandeja por grupos, diálogo de mapeo, CMI). El clon se eliminó y el stack volvió al DW real; el usuario de prueba no existe en el DW real.
- **Defecto real hallado y corregido:** un comentario libre de más de 200 caracteres en la columna de docente se tomaba como nombre de docente y abortaba toda la consolidación (`StringDataRightTruncation`, a mitad de 25.984 registros). Corregido en `resolver_o_crear_docente` con prueba.
- **Diferencia con la medición de la ronda 8:** la UI usa su propia ruta (lectura BETO de los 12.992 registros del lote y consolidación en segundo plano): ≈ 10 min frente a 60 s del ciclo por `/pipeline/process`. Los 185 casos / 12 grupos de la UI no son comparables con los 188 / 37 de la ruta del ciclo. Con 12.992 registros, la consolidación dejó 78.782 hechos (13.106 en revisión) en el clon, sobre todo respuestas de evaluación docente.
- El tiempo humano de lectura y decisión sigue siendo supuesto; lo medido es la respuesta de la UI y la máquina (en `tiempo_klm.json`, bloque `ui_medido_ronda9`).
- El caso de estado fuera de catálogo se sembró en el clon (3 hechos con estado "Retirado"): el flujo no lo generó solo, porque el catálogo real ya contiene las combinaciones de la ronda 7.

## 9. Pruebas y build
Suites: sprint1 16, sprint2 32, sprint3 120, sprint4 23, loops 9, readiness 39 (21 pasadas, 11 omitidas, 7 xfail), transversales 243; 0 fallidas. `npm run build` del frontend termina sin errores; el frontend no tiene pruebas propias (`package.json` no define `test`), la verificación del front es el E2E.

## Límites
Actualización de Power BI sin ejecutar (sin Desktop). Tiempo humano supuesto. E2E sobre clon y con el usuario de prueba. Quedan sin commit `scripts/diccionario_datos_csv.py`, `docs/evidencias/diccionario_datos.csv` y `diccionario_datos.csv` de la raíz (cambios anteriores, no revisados).
