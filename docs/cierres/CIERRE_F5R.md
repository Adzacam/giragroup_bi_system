# CIERRE F5R — 2026-11-19

Rama: `beto-integracion` (sobre `4d79857`).
**Nota de control:** Cifras operativas de la recarga en la DW viva (`giragroup_db`); **no modifican la SFV (`docs/fuente_verdad_tesis.md`)**. No se tocó `frontend/`, `backend/routers/powerbi.py` ni el `.docx` de la tesis.

## Hecho
- **R-0 (Línea base y respaldo):**
  - `pg_dump -Fc` de `giragroup_db` en `output/f5r/giragroup_db_pre_r.dump` (`14.735.448` bytes, `sha256: d942a6df7ea5b906d44a6d22c3a761b32572b054f485e4aff57dee14a5e163ff`).
  - `/health` → `200 OK` (`{"status":"healthy","service":"giragroup-bi-api","database":"connected"}`).
  - Estado previo confirmado: solo `PLANIFICACION` consolidado (`fact_planificacion_programa = 1.663`, `dim_meta = 58`, `dim_modulo = 996`, `carga_fila_origen = 3.442`).
  - Evidencia: `docs/mediciones/f5r_linea_base.json`.
- **R-1 (Carga por la web de los 9 libros faltantes):**
  - Para evitar re-inferencia CPU de >180 s en `PREPARACION_REVISION` (que disparaba `SIN_LATIDO_SEG = 180` con caché vacía en `giragroup_db`), se precargó `cache_indice_beto` (`180.585` entradas desde `output/f3x/giragroup_db_pre_vaciar_20261118.dump`) sobre el dump limpio de R-0, manteniendo intacto el código congelado.
  - Ejecutado vía endpoints reales de DataOps (`scripts/f5r_recarga_web.py`): limpieza de no consolidados previos (`delete-batch`), `upload-batch` de los 9 libros (`id_lote = 35`, `9/9` exitosos, con `tipo_escala = CENTESIMAL_100` para los 2 `ACTA`), `LECTURA_BETO` (`COMPLETADA`, `108.341/108.341`), `preparar-revision` (`COMPLETADA`, `108.341/108.341`) y `confirm-dw-insert` (`COMPLETADA`, `108.341/108.341`).
  - Duración total: `637,22 s` (`10,62 min`), **0 errores 5xx** en `giragroup_api`.
  - Conteos vs `f3v_completo.json`: **Δ = 0** en 16 de 21 tablas (`fact_rendimiento_academico = 25.191`, `fact_evaluacion_docente = 715.217`, `fact_rentabilidad = 95`, `fact_costo_programa = 1.371`, `fact_techo_convenio = 206`, `fact_planificacion_programa = 1.663`, `fact_cobranzas_proyectadas = 0`, `fact_forecast = 0`, `dim_estudiante = 16.873`, `dim_docente = 689`, `dim_tiempo = 2.230`, `dim_origen_documental = 10`, `dim_meta = 58`, `dim_categoria_financiera = 15`, `bridge_modulo_docente = 1.690`, `carga_fila_origen = 1.636.142`).
  - Diferencias explicadas (5 tablas): `dim_modulo` (`4.313` vs `4.527`, Δ `-214`) porque `PLANIFICACION` ya estaba consolidado en el lote #1 con `996` módulos canónicos antes del lote #35 (en `f3v_completo` se cargó 6.º); `fact_situacion_financiera` (`10.733` vs `10.719`, Δ `+14`, con `417` en `requiere_revision = true`), `fact_marketing` (`10.519` vs `10.510`, Δ `+9`), `stg_entidad_no_resuelta` (`10.828` vs `10.762`, Δ `+66`) y `log_inconsistencias` (`27.266` vs `27.918`, Δ `-652`) por consolidación conjunta en un lote tras `PREPARACION_REVISION` frente a consolidación libro a libro en `f3v_completo.py`.
  - Evidencia: `docs/mediciones/f5r_recarga.json`.
- **R-2 (Casos de identidad pendientes, sin aprobar ni descartar):**
  - **1.411** casos pendientes (`resuelto = false`) distribuidos en 4 motivos:
    - `CI_NOMBRE_DISCORDANTE`: **759**
    - `BAJA_CONFIANZA_IA`: **573**
    - `HOMONIMIA`: **70**
    - `CI_DUDOSA`: **9**
  - Más `9.417` registros `RUIDO` descartados automáticamente (`resuelto = true`). Se incluyen 5 ejemplos enmascarados por cada motivo en `docs/mediciones/f5r_casos_pendientes.json`.
- **R-3 (Verificación de uso):**
  - `/api/v1/cmi/scorecard` devuelve **23 KPI** en las 4 gestiones (`2023`: 5 con valor, índice `20,0`; `2024`: 21 con valor, índice `60,9`; `2025`: 21 con valor, índice `65,7`; `2026`: 13 con valor, índice `32,4`).
  - **KPI-23** coincide con `f3v_kpi23_serie.json` con **Δ = 0,0** en todas las gestiones (`2023: null / SIN_UMBRAL`, `2024: 100,00 % / VERDE`, `2025: 99,77 % / VERDE`, `2026: 46,62 % / ROJO`).
  - Alertas (`/api/v1/alertas` `200 OK`: `4.404` críticas, `3.423` advertencias; `/api/v1/riesgos/alertas-tempranas` `200 OK`) y pronósticos (`/api/v1/forecast/analitica-macro?horizonte=6` `200 OK` con los 4 casos) visibles.
  - Capturas reales en navegador (Edge headless, protección de datos personales activa): `output/f5r/captura_cmi.png`, `output/f5r/captura_dataops_ingesta.png`, `output/f5r/captura_dataops_revision.png`.
  - Evidencia: `docs/mediciones/f5r_verificacion_uso.json`.

## Estado para el siguiente paso (Lean / PLAN_F5)
- La DW viva cuenta ahora con los **10 libros cargados** y los **1.411 casos pendientes** en la bandeja de revisión del lote #35 para que Lean los resuelva desde la web y dé acceso RBAC a P01–P10 antes de aplicar el postest Likert (`PLAN_F5.md` queda para el chat 3 sobre el `.docx` y el cálculo del postest tras la recolección).
