# Resumen de Cobertura por Archivo — PLAN F3R-A (2026-11-16)

Auditoría de solo lectura sobre la copia tmpfs `f3r_base` (huella `b5f1d7b1…af24f`, cargada con los recortes del ciclo mensual `2026-03` en `output/backups/f0_lote/slices/`), los 10 libros completos en `uploads/data/` (`90.538` filas procesables, sha256 `aafde8ad…db60`) y la plantilla `dw_vacio`.

## 1. Cuadre por documento en `f3r_base` (recortes `slices/`: 10.816 filas procesables)

| `id_doc` | Archivo | `tipo_fuente` | Filas recorte | Hechos en `f3r_base` | `stg_entidad_no_resuelta` | `log_inconsistencias` | Estado / Hallazgo |
|---|---|---|---|---|---|---|---|
| 1 | `BD Cobranzas.xlsx` | `COBRANZA` | 748 | 725 `fact_situacion_financiera` | 21 | 21 | `Copia de COBRANZAS 2024 2025` no es duplicado (`overlap_CIs = 0`, aporta 446 de 725 hechos). `fact_cobranzas_proyectadas = 0` (`D-A2`). |
| 2 | `BD Egresos.xlsx` | `RENTABILIDAD` | 1.409 | 1.371 `fact_costo_programa` + 12 `fact_rentabilidad` | 15 | 12 | Cuadre conforme a las hojas procesadas. |
| 3 | `BD Techos.xlsx` | `MARKETING` | 1 | 1 `fact_techo_convenio` | 0 | 0 | Fecha `2034-01-12` (`id=25`) fuera de rango 2022–2027 (`D-A5`). |
| 4 | `Base centralizada Académica ARCA (1).xlsx` | `ACTA` | 1.201 | 1.392 `fact_rendimiento_academico` + 5 `bridge_modulo_docente` | 773 | 765 | Hoja `MODULOS` genera fechas `2005-02-05` / `2005-02-14` en `dim_tiempo` con 0 hechos (`D-A5`). |
| 5 | `EJECUTADO VS META.xlsx` | `RENTABILIDAD` | 36 | 79 `fact_rentabilidad` (91 total en tabla con doc 2) | 16 | 21 | 4 filas agregadas interceptadas por BETO NER como `ESTUDIANTE` (`D-A8a`); celda `10.719.694,00` en `META POR CATEGORIA 2024` dic (`D-A8b`). |
| 6 | `Evaluación Docente y Unifranz.xlsx` | `EVALUACION_DOCENTE` | 3.813 | 71.458 `fact_evaluacion_docente` | 1.076 | 1.432 | Despliegue pregunta × fila. |
| 7 | `Experiencia Docente 2.0.xlsx` | `ACTA` | 1.137 | 0 hechos | 1.137 | 1.211 | **Defecto `D-A4`**: etiquetado `evaluacion_docente` en staging (`ingestion_service.py:837`), pero `consolidacion.py:193-200` rutea por `dim_origen_documental.tipo_fuente='ACTA'`, descartando 100 % (1.137 recorte / 16.629 libro). |
| 8 | `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR_S).xlsx` | `RENTABILIDAD` | 1.254 | 0 hechos | 1.911 | 2.302 | Hojas de planificación sin estructura de rentabilidad; descartes en staging/log. |
| 9 | `TBL_INSCRITOS.xlsx` | `ADMISION` | 391 | 299 `fact_marketing` (391 inscritos; 782 `carga_fila_origen`) | 2 | 1 | Ciclo `2026-03` esperado en `f3_base`; en `dw_vacio` existen 15.196 filas huérfanas (`D-A9`). |
| 10 | `_BBDD_ ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx` | `EVALUACION_DOCENTE` | 882 | 3.615 `fact_evaluacion_docente` | 125 | 461 | **Defecto `D-A4b`**: 18 filas de `TBL EXPERIENCIA UNIFRANZ` usan la 1.ª fila de datos como cabecera (`BAJA_CONFIANZA_IA`). |

## 2. Defectos registrados (solo lectura, sin corrección en código)

1. **`D-A9` (`dw_vacio`)**: `scripts/aislada_tmpfs.sh:16` trunca 15 tablas pero omite `public.carga_fila_origen`, dejando `15.196` filas huérfanas (`id_documento=12`, `tabla='fact_marketing'`). Al cargar `uploads/data/TBL_INSCRITOS.xlsx` completo sobre `dw_vacio`, `fact_marketing` queda en `0` (`15.183` filas bloqueadas por `backend/services/dw_loader.py:1019-1029`). Evidencia: `docs/mediciones/f3r_dw_vacio.json`.
2. **`D-A4` (`Experiencia Docente 2.0.xlsx`)**: `ingestion_service.py:837` etiqueta las filas como `evaluacion_docente` en `staging_registros_crudos`, pero `consolidacion.py:193-200` rutea por `dim_origen_documental.tipo_fuente='ACTA'` e ignora `stg.categoria`, descartando el 100 % del archivo (`1.137` filas en recorte / `16.629` en el libro completo).
3. **`D-A4b` (`TBL EXPERIENCIA UNIFRANZ`, doc 10)**: `18` filas toman la 1.ª fila de datos como cabecera (`BAJA_CONFIANZA_IA`).
4. **`D-A5` (`dim_tiempo` fuera de rango 2022–2027)**: incluye `2034-01-12` (`BD Techos.xlsx` f.26, `1` hecho en `fact_techo_convenio` `id=25`) y `2005-02-05` / `2005-02-14` (`ARCA` hoja `MODULOS`, `0` hechos).
5. **`D-A8a` (`EJECUTADO VS META.xlsx`)**: BETO NER intercepta `4` filas agregadas (`PROGRAMAS JUNIO`, `TECHOS/CERRADOS FEBRERO/ABRIL/OCTUBRE`) como `ESTUDIANTE` (`BAJA_CONFIANZA_IA`, `id_staging` `812-815`), reduciendo `fact_rentabilidad` de `95` esperados a `91` en `f3r_base`.
6. **`D-A8b` (`META POR CATEGORIA 2024`)**: celda `10.719.694,00` (`TECHOS/CERRADOS` diciembre) distorsiona `KPI-02`/`KPI-03` de gestión `2024` (`kpi_service.py:320-347`); no afecta a `META_MENSUAL_PROGRAMAS` (`forecast_service.py:470`).
7. **`D-A2` (`fact_cobranzas_proyectadas`)**: `0` filas; no existe extractor implementado.
