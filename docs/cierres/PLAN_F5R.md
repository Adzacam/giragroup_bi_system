# PLAN F5R — 2026-11-19
Objetivo de la fase: dejar la DW viva con los 10 libros cargados con el código congelado, para que las 10 personas del pretest (P01–P10) usen el sistema completo antes del postest Likert.
Entrada: `CIERRE_F3V.md` (V-9: la DW viva solo tiene PLANIFICACION, 1.663 filas en `fact_planificacion_programa` y 58 en `dim_meta`); rama `beto-integracion` `595e40f`. **Decisión de Lean (19-nov): recargar.**

| ID | Tarea | Agente | Depende de | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|
| R-0 | Línea base y respaldo: `pg_dump -Fc` de `giragroup_db` a `output/f5r/giragroup_db_pre_r.dump` (con su sha); conteos por tabla, lotes y documentos; comprobar que los contenedores corren el código congelado (hash del commit en la imagen o build reciente) y que `/health` da 200 | dev-baja | — | 1) sha del dump; 2) conteos; 3) commit del código desplegado | `f5r_linea_base.json` |
| R-1 | **Carga por la web** (endpoints reales de DataOps, como un usuario) de los **9 libros que faltan** de `uploads/data/` (lote `aafde8ad…db60`, sin `uploads/otras_versiones/`): Lectura de BETO → Revisión → Consolidar. PLANIFICACION no se vuelve a cargar | dev-baja | R-0 | 1) 9/9 documentos con las tareas `COMPLETADA`; 2) 0 errores 5xx en `giragroup_api`; 3) los conteos por tabla igualan los de `f3v_completo.json` (±0) o cada diferencia está explicada (casos que quedaron en revisión) | `f5r_recarga.json` |
| R-2 | Casos de identidad: **no se aprueban ni se descartan solos**. Se listan por motivo (cantidad y 5 ejemplos enmascarados) para que Lean los resuelva desde la web | dev-baja | R-1 | conteo por motivo | `f5r_casos_pendientes.json` |
| R-3 | Comprobación de uso: el scorecard muestra los **23 KPI** con valor donde corresponde, KPI-23 por gestión igual a `f3v_kpi23_serie.json`, alertas y pronósticos visibles; capturas del CMI y de DataOps para el registro (con la máscara activada) | dev-baja | R-1 | 1) 23 KPI en `/api/v1/cmi/scorecard`; 2) KPI-23 con Δ = 0 frente a la serie congelada | `f5r_verificacion_uso.json` |

## Control
- **Estos números son de operación, no de la tesis.** La SFV no cambia; las cifras congeladas salen del snapshot, de f3_base y de f3v_completo. Los tiempos de esta carga no son RNF-03 (la caché de BETO ya está poblada).
- Si los conteos no cuadran con `f3v_completo` y la diferencia no se explica por casos en revisión, se detiene y se avisa. Se puede volver al dump de R-0.
- Ningún commit de `frontend/` ni de `backend/routers/powerbi.py`. Las credenciales de la cuenta las escribe Lean en el navegador; no se guardan en archivos.

## Después (Lean)
Resolver los casos de R-2, dar acceso a P01–P10 con su rol RBAC y, tras un período de uso (1–2 semanas), aplicar el postest en la columna «Con el sistema» de cada encuesta, con fecha. Con las respuestas, el chat 2 o el chat 4 calcula la Tabla 4.9 y el Gráfico 4.6 (`f5_likert_postest.*`).

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F5R.md: respaldo de la DW viva (pg_dump) y carga por la web de los 9 libros que faltan (todos menos PLANIFICACION), con el código congelado. No apruebes ni descartes casos de identidad: solo lístalos. Los conteos se comparan con f3v_completo.json. No toques la SFV ni el frontend. Escribe CIERRE_F5R.md.
