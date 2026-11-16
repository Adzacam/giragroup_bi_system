# CIERRE F3R-A — Auditoría de Cobertura por Archivo (2026-11-16)

## 1. Alcance y control de solo lectura
- Se ejecutó la auditoría de `docs/cierres/PLAN_F3R_A.md` en **estricto solo lectura** sobre `f3r_base` (huella `b5f1d7b145ceeef8ca85c1f85fd9121eb20d506fcad618a13d66fd944eaaf24f`), `uploads/data/` (`90.538` filas procesables, sha256 `aafde8ad…db60`) y `output/backups/f0_lote/slices/` (`10.816` filas procesables, ciclo mensual `2026-03`).
- **Cero cambios en código:** `backend/`, `pipeline/`, `frontend/`, DW viva, `docs/evidencias/snapshot_dw_20261110_1201.dump` y `.docx` sin modificaciones.

## 2. Resumen de cobertura y defectos registrados

| ID Defecto | Archivo / Componente afectado | Síntoma / Causa raíz | Impacto en SFV y KPIs |
|---|---|---|---|
| `D-A9` | `scripts/aislada_tmpfs.sh:16` / `dw_loader.py:1019-1029` | Omite `TRUNCATE` de `public.carga_fila_origen`, dejando `15.196` filas huérfanas (`id_documento=12`, `fact_marketing`). Bloquea `15.183` filas si se carga `TBL_INSCRITOS.xlsx` completo sobre `dw_vacio`. | No altera el recorte `2026-03` de `f3_base`, pero explica `carga_fila_origen = 15.978` (`15.196 + 782`). |
| `D-A4` | `Experiencia Docente 2.0.xlsx` (`consolidacion.py:193-200`) | `ingestion_service.py:837` etiqueta `evaluacion_docente`, pero `consolidacion.py` rutea por `tipo_fuente='ACTA'`. Descarta `100 %` (`1.137` recorte / `16.629` libro). | Subrepresentación de `fact_evaluacion_docente` proveniente de este libro. |
| `D-A4b` | `TBL EXPERIENCIA UNIFRANZ` (`doc 10`) | `18` filas toman la 1.ª fila de datos como cabecera (`BAJA_CONFIANZA_IA`). | Derivación a staging/bandeja en `doc 10`. |
| `D-A5` | `dim_tiempo` (`BD Techos.xlsx`, `ARCA MODULOS`) | Fechas fuera de 2022–2027: `2034-01-12` (`1` hecho en `fact_techo_convenio` `id=25`) y `2005-02-05`/`2005-02-14` (`0` hechos). | Amplía rango `dim_tiempo` a `2005-02-05`..`2034-01-12`. |
| `D-A8a` | `EJECUTADO VS META.xlsx` | BETO NER intercepta `4` filas agregadas (`PROGRAMAS JUNIO`, `TECHOS/CERRADOS FEBRERO/ABRIL/OCTUBRE`) como `ESTUDIANTE` (`BAJA_CONFIANZA_IA`, `id_staging` `812-815`). | `91` filas en `fact_rentabilidad` frente a `95` esperadas en `f3r_base`. |
| `D-A8b` | `META POR CATEGORIA 2024` (`TECHOS/CERRADOS` dic) | Celda `10.719.694,00` (posible total anual en celda mensual). | Distorsiona `KPI-02`/`KPI-03` 2024 (`kpi_service.py:320-347`); no afecta `META_MENSUAL_PROGRAMAS`. |
| `D-A2` | `fact_cobranzas_proyectadas` | Sin extractor implementado. | Tabla en `0` filas. |

- Hallazgo adicional verificado: `Copia de COBRANZAS 2024 2025` en `BD Cobranzas.xlsx` **no** es duplicado (`overlap_CIs = 0`, aporta `446` de `725` hechos financieros en `f3r_base`).

## 3. Artefactos generados
- `docs/mediciones/f3r_dw_vacio.json`
- `docs/mediciones/f3r_cobertura_resumen.md`
- `docs/cierres/CIERRE_F3R_A.md`

## 4. Decisión registrada para R3-12
- Lean confirmó la **Opción 1** para la Sección E (snapshot, `n = 43`) con la nota explícita sobre el ciclo mensual `2026-03` de `f3_base` (`slices/`).
- Los defectos `D-A9`, `D-A4`, `D-A4b`, `D-A5`, `D-A8a`, `D-A8b` y `D-A2` quedan **registrados como limitaciones técnicas** en la Sección H de la SFV (`docs/fuente_verdad_tesis.md`) sin modificar el código del sistema en F3R.
