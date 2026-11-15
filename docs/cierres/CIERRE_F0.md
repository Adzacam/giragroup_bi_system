# CIERRE F0 — 14 de noviembre de 2026

Rama / commit: `beto-integracion` · medido en `16bba9f6a662233841b8a3b46f0d98354931e218` · cierre en commit selectivo F0 (`F0: medición aislada y evidencia BETO`).

Hecho (máx. 10 líneas):
- F0-P: lote congelado (10 originales + 10 slices, `sha256: aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60`), snapshot `snapshot_dw_20261110_1201` y `catalogo_copia` verificados sin diferencias antes/después.
- A-1 y A-2: **42 corridas válidas** (7 configs × 2 estados de caché × 3 réplicas) en `tmpfs`, excluyendo 7 calentamientos y 2 intentos descartados (`f0_a0_vacia_r2`, `f0_a0_llena_r1`), agregadas en `f0_ablacion.json`/`.csv` y `f0_ventana.json`.
- A-2 puerta `< 20 %`: `a2` sin ventana = `34,09 %` (`1.734 / 5.087`, no cumple); `a2w` (ventana stride 32) = `17,89 %` (`1.035 / 5.786`, cumple; `2245,73 s` en caché vacía y `216,28 s` en caché llena).
- A-3 y A-6: población de `90` contextos `DESACUERDO` en `f0_desacuerdos_muestra.csv`/`.json` y `2.472` filas de impacto QC en `f0_impacto_qc.csv`/`.json`.
- A-4: paquete ciego sellado con `7` casos elegibles (`f0_top1_candidatos.csv`, `f0_top1_resumen.json`), listo para revisión humana independiente.
- B-3: evaluación sobre `gold_510` (A/B `F1=1,0`; C estricto `F1=0,9776`, relajado `F1=0,9912`) y conciliación de `503` histórico por matriz fija (`PROGRAMA=173` vs `180`).
- B-4: auditoría de corpus (`0` duplicados textuales, pero `1` estudiante y `143` docentes normalizados compartidos en train–dev; revisión humana histórica del gold no verificable).
- B-5: conciliación 2025 en `beto_pg_tmpfs` (`12.907.977,61 Bs` observado vs `12.747.275,66 Bs` ajustado OLS anual, delta `-1,24 %`).
- B-10: credencial PostgreSQL retirada de archivos actuales y parametrizada por entorno (`f0_b10_saneamiento.json`).

No hecho y por qué:
- **A-4 (`top-1`)**: queda pendiente (`N/D`, `0` decisiones humanas válidas) porque no existen decisiones humanas independientes previas y `PLAN_F0.md` prohíbe usar `simular_revision.py` como verdad humana.
- **Validación humana de A-3**: queda en estado de sugerencia técnica automática (`automatic_technical_suggestions_review_pending`); requiere etiquetado humano independiente.
- **Referencia `73ec78f` sobre el lote F0**: no ejecutada en esta fase; queda declarada pendiente sin reutilizar huellas de otros lotes.
- **B-10 rotación/reescritura de historial git**: requiere decisión explícita de Lean.

Invariantes cambiados: no.

Pruebas: `802` colectadas / `784` passed / `0` failed / `11` skipped / `7` xfailed · cobertura `70 %` (`14.555` sentencias, `4.345` no cubiertas) sobre copia aislada en `beto_pg_tmpfs` (`docs/mediciones/f0_pytest_cobertura.txt`).

Servicios reconstruidos + estado de docker compose ps:
Reconstruidos `api`, `pipeline` y `catalog_db` tras saneamiento B-10; 9 servicios `Up` (`db` y `catalog_db` `healthy`), `api /health` `healthy`, `pipeline /health` `online` (`BETO_PYTORCH_REAL`), `api /api/v1/cmi/scorecard` `401 Unauthorized` (solo lectura). `beto_pg_tmpfs` desmontado (`aislada_tmpfs.sh down`). Evidencia en `docs/mediciones/f0_servicios.txt`.

Cambios de esquema o API: ninguno (solo parametrización de conexión por variable de entorno en B-10 y scripts/pruebas de medición F0).

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `a0_vacia` tiempo máquina media ± DE | `803,58 ± 173,04 s` (`13,39 min`) · `bandeja 182 / manuales 59 / KPI-18 59` | `f0_ablacion.csv`
- `a0_llena` tiempo máquina media ± DE | `210,08 ± 7,24 s` (`3,50 min`) · `bandeja 182 / manuales 59 / KPI-18 59` | `f0_ablacion.csv`
- `a1_vacia` / `a1_llena` tiempo máquina | `739,61 ± 11,12 s` (`12,32 min`) / `206,33 ± 1,74 s` (`3,44 min`) · `182 / 59 / 59` | `f0_ablacion.csv`
- `a2_vacia` tiempo máquina | `1110,33 ± 89,81 s` (`18,50 min`) · `bandeja 201 / manuales 71 / KPI-18 71` | `f0_ablacion.csv`
- `a12_vacia` / `a12_llena` tiempo máquina | `1065,35 ± 0,51 s` (`17,76 min`) / `218,44 ± 1,67 s` (`3,64 min`) · `201 / 71 / 71` | `f0_ablacion.csv`
- `a123_vacia` / `a123_llena` tiempo máquina | `1068,30 ± 2,09 s` (`17,81 min`) / `219,82 ± 1,81 s` (`3,67 min`) · `201 / 71 / 71` | `f0_ablacion.csv`
- `a2w_vacia` / `a2w_llena` tiempo máquina | `2245,73 ± 111,13 s` (`37,43 min`) / `216,28 ± 8,58 s` (`3,60 min`) · `224 / 82 / 82` | `f0_ablacion.csv`
- A-2 razón `no_evaluables / comparadas_acuerdo` | `a2 = 34,09 %` (`1.734 / 5.087`) · `a2w = 17,89 %` (`1.035 / 5.786`) | `f0_ventana.json`
- A-3 población `DESACUERDO` / A-4 elegibles `top-1` | `90` contextos / `7` casos (`top1 = N/D`) | `f0_desacuerdos_resumen.json`, `f0_top1_resumen.json`
- B-3 `gold_510` F1 Modo A / B / C (estricto; relajado) | `1,0` / `1,0` / `0,9776` (`0,9912`) · soporte `510` | `f0_b3_ablacion.csv`, `f0_b3_conteos.json`
- B-5 2025 observado vs ajustado OLS anual | `12.907.977,61 Bs` vs `12.747.275,66 Bs` (`-1,24 %`) | `f0_b5_2025.json`

Impacto en el documento (sección o tabla):
Ninguno directo en F0 (prohibido editar `.docx` o `docs/fuente_verdad_tesis.md` hasta F3). Las cifras anteriores alimentarán la decisión de flags en `PLAN_F1.md`.

Riesgos abiertos:
- `a2w` en caché vacía (`37,43 min`) y `a2`/`a12`/`a123` en caché vacía (`17,76–18,50 min`) superan la meta RNF-03 de `15 min` (y `a2w` supera el aceptable `20 min`).
- Faltan decisiones humanas independientes para sellar A-4 (`top-1`) y validar A-3 (`DESACUERDO`).
- Fuga de pool de personas entre train y dev (`143` docentes, `1` estudiante) y ausencia de registro verificable de revisión humana del gold en B-4.
- Secreto PostgreSQL histórico permanece en commits anteriores del historial git hasta que Lean autorice rotación/reescritura.

Pendiente para el chat 4:
No aplica en F0 (las figuras y actualización de tesis corresponden a F3/F4 según `PLAN_F0.md`).
