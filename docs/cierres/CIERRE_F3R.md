# CIERRE F3R — Reconciliación Integral y SFV Unificada (2026-11-16)

## 1. Resumen ejecutivo
Se completaron las tareas **R3-1..R3-12** de `docs/cierres/PLAN_F3R.md` y la auditoría de cobertura **PLAN_F3R_A.md** (`A-0..A-9`), consolidando `docs/fuente_verdad_tesis.md` como **Única Fuente de Verdad (SFV)** unificada bajo la base mixta declarada por Lean (16-nov-2026):
- **`snapshot 10-nov` (`snapshot_dw_20261110_1201`)**: series de negocio e históricas independientes del modelo (KPIs de negocio, alertas tempranas, Holt-Winters de matrícula con `n_obs=43` bajo la Opción 1 confirmada, `META_MENSUAL_PROGRAMAS` y `META_ANUAL` OLS).
- **`f3_base` (ciclo mensual `2026-03` en `slices/`)**: métricas operativas del ciclo (tiempos RNF-03, KLM con `W_medido=0,089 s`, bandeja `680/19`, staging `5.076`, bitácora `B-9` `6.226`, `KPI-10`, `KPI-11`, `KPI-18`, cuadre `KPI-15`, inventario DW y API).
- **`lote 1.387` (`f3r_lote_1387.json`)**: evaluación controlada reejecutada con el modelo BETO vigente (`98,05 %` directo, `27` HITL, `0` staging, `0` excepciones sin control).

**Nota:** Este cierre **no** declara «F3 congelado»; la revisión final y el anuncio corresponden al orquestador (Chat 1). No se realizó `git commit`.

## 2. Resumen de tareas R3-1..R3-12 y `PLAN_F3R_A.md`

| Bloque / Tarea | Estado | Evidencia principal en `docs/mediciones/` |
|---|---|---|
| **R3-1** Reconstrucción `f3_base` (huella `b5f1d7b1…af24f`) | Completada | `f3r_base_reproducida.json`, `f3r_extraccion_f3base.json`, `f3r_consultas.sql` |
| **R3-2** Cuadre `KPI-15` por fila de origen | Completada | `f3r_kpi15_cuadre.json` (`500` Mora / `7` Prev / `218` Vigente, `Δ=0`) |
| **R3-3** `schema_migrations` en corridas llenas | Completada | `f3r_schema_migrations.json` (`13` filas; solo varía `applied_at`) |
| **R3-4** Diagnóstico matrícula en lote (`ALUMNOS_GLOBAL`) | Completada | `f3r_matricula_lote.json` (`1` mes `2026-03` → `n_obs=0`) |
| **R3-5** Lote `1.387` con modelo BETO vigente | Completada | `f3r_lote_1387.json`, `f3r_lote_1387_r2.json` |
| **R3-6** Cifras de negocio y HW/OLS en snapshot | Completada | `f3r_snapshot_kpi.json`, `f3r_snapshot_alertas.json`, `f3r_hw_matricula.json`, `f3r_ols_snapshot.json`, `f3r_b5_snapshot_sql.txt` |
| **R3-7** Suite `pytest` y cobertura | Completada | `f3r_pruebas.json` (`842` colectadas, `823` passed, `1` failed por cambio previo en `powerbi.py`, `70,27 %`), `f3r_cobertura_archivos.csv` |
| **R3-8** Locust, Newman y $W$ medido del KLM | Completada | `f3r_locust.json`, `f3r_newman.json`, `f3r_klm_w_medido.json` (`W=0,089 s` → KLM `221,3 s`, vacía+KLM `1.071,48 s`, llena+KLM `477,45 s`) |
| **R3-9** Inventarios y evidencias sueltas | Completada | `f3r_inventario_corpus.json`, `f3r_inventario_api.json` (`136` rutas), `f3r_evidencias_sueltas.json` |
| **R3-10** Ablación y matriz de confusión | Completada | `f3r_ablacion.json`, `f3r_matriz_confusion.json` (`503` TP estricto / `510` relajado) |
| **R3-11** Mapa resuelto Sección J | Completada | `f3r_mapa_j.json` (`sin_resolver = 0`) |
| **PLAN_F3R_A** Cobertura por archivo y `dw_vacio` | Completada | `f3r_dw_vacio.json`, `f3r_cobertura_resumen.md`, `docs/cierres/CIERRE_F3R_A.md` |
| **R3-12** SFV unificada y verificación | Completada | `docs/fuente_verdad_tesis.md`, `f3_sfv_trazabilidad.json`, `scripts/verificar_sfv.py`, `f3r_sfv_verificacion.txt` (`0 / 0 / 0`) |

## 3. Verificación final de SFV (`R3-12`)
- Comando ejecutado: `.venv/Scripts/python.exe scripts/verificar_sfv.py > docs/mediciones/f3r_sfv_verificacion.txt`
- Exit code: `0`
- Resultado: `RESUMEN: total=143 discrepancias=0 cifras_sin_fuente=0 menciones_v1_v2=0 (0 / 0 / 0)`

## 4. Control de cambios y archivos fuera de F3R
- **Cero cambios realizados por F3R/F3R-A en:** `backend/`, `pipeline/`, `frontend/`, DW viva, `docs/evidencias/snapshot_dw_20261110_1201.dump` y archivos `.docx`.
- **Cambios previos de Lean sin commit (fuera de F3R, no incluir en el commit selectivo de F3R):**
  - `backend/routers/powerbi.py`
  - `frontend/index.html`, `frontend/src/App.jsx`, `frontend/src/api/powerbiApi.js`, `frontend/src/components/layout/Navbar.jsx`, `frontend/src/components/shared/GlosarioFlotante.jsx`, `frontend/src/modules/academic/ProyeccionAlumnos.jsx`, `frontend/src/modules/academic/RendimientoAlertas.jsx`, `frontend/src/modules/admin/AuditoriaSistema.jsx`, `frontend/src/modules/admin/CuadroMandoIntegral.jsx`, `frontend/src/modules/admin/cmi/*`, `frontend/src/modules/dataops/*`, `frontend/src/modules/finance/MetasGestion.jsx`, `frontend/src/modules/notifications/NotificationsPage.jsx`, `frontend/src/modules/reports/CentroReportes.jsx`, `frontend/src/services/notificationService.js`, `frontend/src/services/sileoToast.js`, `frontend/src/styles/tokens.css`, `frontend/src/v2/`
  - `docs/cierres/PLAN_FRONT_V2.md`, `docs/cierres/CIERRE_FRONT_V2.md`
