# PLAN F13_SINCRONIZACION_SFV — 2026-11-25

Objetivo de la fase (1 línea): Sincronizar y recongelar `docs/fuente_verdad_tesis.md` contra los cierres `CIERRE_F9`..`CIERRE_F12` y sus evidencias en `docs/mediciones/f9_*`, `f10_*`, `f11_*` y `f12_*` (respetando la Regla de no mezcla de bases), verificando el resultado con `scripts/verificar_sfv.py` para traspaso a Chat 3.

Entrada: CIERRES previos leídos = `docs/cierres/CIERRE_F9_RNF03_INDICE.md`, `CIERRE_F10_DATAOPS_UX_IDEMPOTENCIA.md`, `CIERRE_F11_PREDEFENSA_SEMILLA.md`, `CIERRE_F12_REVISION_GRUPOS_UX.md`; rama base = `main` (`13b6173`); verificador = `scripts/verificar_sfv.py`.

## Tabla de tareas

| ID | Frente | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|---|
| F13-0 | Pre-vuelo | Auditar las rutas JSON exactas dentro de `docs/mediciones/f9_completo.json`, `f9_aporte_10archivos.json`, `f9_kpi10_check.json`, `f9_invariantes.json`, `f11_carga_limpia.json`, `f11_backup_verificacion.json`, `f11_beto_check.json` y los textos `f10_*`, `f12_*` para garantizar trazabilidad 1 a 1 con el formato que espera `scripts/verificar_sfv.py` | `dev-baja` | — | — | Inventario de claves JSON reales verificadas; `0` rutas inexistentes | `f13_rutas_sfv.json` |
| F13-1 | Encabezado y Reglas de bases (`docs/fuente_verdad_tesis.md`) | Actualizar la cabecera de `docs/fuente_verdad_tesis.md`: (1) Estado **CONGELADO — 25 de noviembre de 2026 (recongelado tras F9–F12)**; (2) Rama / Commit base `main` (`13b6173`); (3) Flags vigentes de producción (`BETO_CASCADA_FINAL=True`, `BETO_ACUERDO_QC=True` [acotado a `FUZZY`], `BETO_SUGERENCIA_HITL=True` [corte `80,0`], `BETO_RESCATE_ACADEMICO=True` [acotado a hojas sin columna estructurada], `BETO_VENTANA=False`); (4) Añadir en «Regla de bases declaradas» las nuevas bases separadas (`f9_completo`, `f11_lote1_predefensa`, `f12_bandeja_lote1`) sin alterar ni mezclar las tablas existentes de `snapshot 10-nov`, `lote 1.387` y `f3_base` | `dev-media` | F13-0 | — | Cabecera y catálogo de bases 100 % consistentes con `pipeline/config.py` y `CIERRE_F9`..`F12`; regla de no mezcla respetada | `f13_sfv_diff_cabecera.txt` |
| F13-2 | Tablas nuevas F9–F12 en `docs/fuente_verdad_tesis.md` | Incorporar (o actualizar con base explícita en cada título, estándar numérico Bolivia coma decimal / punto miles) las cifras verificadas de: (1) **RNF-03 y ablación F9 (`f9_completo.json`, `f9_aporte_10archivos.json`, `f9_kpi10_check.json`):** carga histórica fría 10 libros = **`655,91 s` (`10,93 min` < `15 min`, `rnf03_cumplido_15m = true`)**, lote 10 archivos Modo B = **`119,82 s` (`2,00 min`)** con **`141`** casos en bandeja, `KPI-10` gestión 2025 = **`99,99`** (`VERDE`, `27.190/27.190` poblados, media `0,9836`), `pytest` = `121 passed, 1 skipped, 0 failed`; (2) **Idempotencia y UX DataOps F10 (`f10_p0_idempotencia_test.txt`, `f10_pruebas_back.txt`):** `0` duplicados al navegar Paso 2 ↔ Paso 3, `119 passed` backend / `25` archivos Vitest; (3) **Carga limpia Lote #1 y Semilla Pre-Defensa F11 (`f11_carga_limpia.json`, `f11_backup_verificacion.json`, `f11_beto_check.json`):** **`490.549` hechos insertados** (`fact_rendimiento_academico`: `23.773`, `fact_situacion_financiera`: `27.150`, `fact_evaluacion_docente`: `409.645`, `fact_forecast`: `32` con `n_observaciones = 43`), `14.365` hechos en revisión, **`1.573` casos staging HITL**, restauración de `backups/snapshot_pre_defensa.dump` (`65,24 MB`) verificada en **`9,36 s`**, UI oficial en rutas raíz `/` sin `/v2` ni botón `V1` (`25` archivos / `129` tests Vitest); (4) **Bandeja HITL y Gobernanza F12 (`f12_grupos_api_test.txt`, `f12_gobernanza_batch_test.txt`, `f12_pruebas_back.txt`):** Lote #1 (`1.573` staging / `1.578` totales con `5` hechos) reducido de `839` grupos (`168` págs.) a **`126` grupos (`26` págs.)**, `251` casos prioridad `ALTA`, guardrail `HTTP 422` para `CI_NOMBRE_DISCORDANTE < 30`, `17 passed` backend / `129 passed` frontend | `dev-media` | F13-1 | — | Cada fila nueva apunta a un archivo existente en `docs/mediciones/f9_*..f12_*` con ruta JSON exacta; estándar numérico Bolivia respetado; 0 cifras inventadas | `f13_sfv_verificacion.txt` |
| F13-3 | Verificación automática, commit y cierre | (1) Ejecutar `python scripts/verificar_sfv.py` sobre `docs/fuente_verdad_tesis.md` y confirmar `0` errores; (2) Verificar que `snapshot_dw_20261110_1201` y `Lote #1` no fueron tocados y que no hay credenciales/PII en el diff; (3) Hacer commit `F13: recongelamiento docs/fuente_verdad_tesis.md (F9–F12)` y escribir `docs/cierres/CIERRE_F13_SINCRONIZACION_SFV.md` con aviso «SFV recongelado» para Chat 3 | `dev-baja` | F13-2 | — | `python scripts/verificar_sfv.py` termina con código `0`; commit limpio; `CIERRE_F13_SINCRONIZACION_SFV.md` escrito | `f13_sfv_verificacion.txt`, `docs/cierres/CIERRE_F13_SINCRONIZACION_SFV.md` |

## Comandos exactos por tarea
- Auditoría de rutas (`F13-0`): inspección de solo lectura de `docs/mediciones/f9_*.json`, `f11_*.json`, `f10_*`, `f12_*`.
- Verificación SFV (`F13-3`): `python scripts/verificar_sfv.py` (guardar salida en `docs/mediciones/f13_sfv_verificacion.txt`).
- Estado y commit (`F13-3`): `git diff --stat docs/fuente_verdad_tesis.md` y commit limpio.

## Riesgos y control
- **Regla de no mezcla de bases:** No sobreescribir las filas de `snapshot 10-nov`, `lote 1.387` ni `f3_base` con cifras de `f9_completo` o `f11_carga_limpia`; agregar tablas dedicadas con su base declarada en el título y actualizar el veredicto de RNF-03 citando explícitamente la evolución `f5c_b7_corridas.json` → `f9_completo.json`.
- **No tocar código ni BD:** Esta fase es estrictamente documental sobre `docs/fuente_verdad_tesis.md` y `docs/cierres/CIERRE_F13_SINCRONIZACION_SFV.md`; no se modifican servicios, no se hace rebuild ni se toca `giragroup_db` ni `snapshot_dw_20261110_1201`.
- **No tocar el `.docx`:** El documento de tesis se actualiza únicamente desde Chat 3 usando el `docs/fuente_verdad_tesis.md` recongelado.

## DECISIONES PENDIENTES PARA LEAN
- Ninguna (el usuario ya solicitó explícitamente la sincronización de `docs/fuente_verdad_tesis.md` con las cifras de F9–F12).

Al cerrar: `python scripts/verificar_sfv.py` (`exit 0`) · commit `F13: recongelamiento SFV` · `CIERRE_F13_SINCRONIZACION_SFV.md` · aviso «SFV recongelado» para Chat 3.

## PROMPT PARA CHAT 2
```text
/gira-desarrollar
Ejecuta `docs/cierres/PLAN_F13_SINCRONIZACION_SFV.md` en orden (F13-0 → F13-1 → F13-2 → F13-3).
Actualiza `docs/fuente_verdad_tesis.md` respetando estrictamente la Regla de no mezcla de bases (mantén intactas las tablas de `snapshot 10-nov`, `lote 1.387` y `f3_base`, y agrega/actualiza las secciones dedicadas para `f9_completo`, `f11_lote1_predefensa` y `f12_bandeja_lote1` con estándar numérico Bolivia: coma decimal y punto de miles).
Verifica con `python scripts/verificar_sfv.py` que todas las rutas y cifras pasan sin errores (`exit 0`). No toques código, contenedores, `giragroup_db`, `snapshot_dw_20261110_1201` ni el `.docx`.
Usa `dev-baja` para `F13-0` y `F13-3`, y `dev-media` para `F13-1`/`F13-2`. Al terminar, haz commit, escribe `docs/cierres/CIERRE_F13_SINCRONIZACION_SFV.md` e indica «SFV recongelado» para Chat 3.
```
