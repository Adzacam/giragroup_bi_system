# CIERRE F10_DATAOPS_UX_IDEMPOTENCIA — 2026-11-25

- **Plan ejecutado:** `docs/cierres/PLAN_F10_DATAOPS_UX_IDEMPOTENCIA.md`
- **Rama base:** `main` (`e93533a`)
- **Snapshot protegido:** `snapshot_dw_20261110_1201` intacto.

## Resumen por tarea

| ID | Prioridad | Estado | Evidencia en `docs/mediciones/` | Resultado medido |
|---|---|---|---|---|
| F10-0 | Pre-vuelo | Completado | `f10_p0_diagnostico.json` | Auditoría en `giragroup_db`: `2440` filas en `stg_entidad_no_resuelta` (multiplicación originada porque `evaluacion.py` persistía `BAJA_CONFIANZA` con `line` completo y sin aplicar `fila_resuelta_por_regla`, mientras `consolidacion.py` insertaba `BAJA_CONFIANZA_IA` con `line[:250]` y `dw_loader` no normalizaba ni deduplicaba en Fase A). |
| F10-1 | **P0** | Completado | `f10_p0_idempotencia_test.txt` | Idempotencia estricta en `evaluacion.py`, `consolidacion.py` y `dw_loader.py` (clave normalizada `" ".join(texto.split())[:250]` compartida entre Paso 2 y Paso 3); `extraccion_por_encabezado.py` añade `registros_asignacion_docente(campos)` en `fila_resuelta_por_regla` para `#5888` y `evaluacion.py` respeta `fila_resuelta_por_regla` para `#4233`/`#4149`. Prueba `tests/sprint5/test_f10_p0_idempotencia_hitl.py`: **2 passed** (`0 failed`). |
| F10-2a | **P1** | Completado | `f10_p1_ingesta_ux.md` | Sincronizados toasts y estado de carga en `IngestView.jsx` (toast único de transferencia, fin inmediato de spinner y botón `Ir a Lectura de BETO` sin auto-disparar BETO); `ProgresoTarea.jsx` unifica porcentaje y suaviza `restante_seg` con EMA. |
| F10-2b | **P1** | Completado | `f10_p1_flujo_vivo.md` | Polling en vivo en `useLecturaBeto.js` y `BetoReadingFlowView.jsx`, botón `Consolidar / Insertar al DW`, banner con `Ir a Revisión` hacia `?vista=PENDIENTES` y lectura de `vista` en `HumanReviewFlowView.jsx`. |
| F10-3a | **P2** | Completado | `f10_p2_paso2_check.md` | Header estable en Paso 2 sin layout shift, `RegistroBetoRow.jsx` sin duplicación de `raw_text`, y modal `BetoMetricasModal.jsx` / `BetoMetricasTablas.jsx` / `betoMetricas.json` con tabla de **ablación Modo A vs. Modo B** (`f9_aporte_10archivos.json`) y cifras vigentes de F9 (`10,93 min` < `15 min` RNF-03, `99,52 %` tasa de acuerdo). |
| F10-3b | **P2** | Completado | `f10_p2_paso3_check.md` | `revision_formularios.py` y `revision_hechos.py` muestran `en la banda baja (< 0,60)` cuando `confianza < 0.60`; `CasoDetallePanel.jsx` contextualiza chips por área + recomendación y colapsa la línea original IOB2 en un solo `<details>`. |
| F10-4 | **P3** | Completado | `f10_p3_ux_motion_check.md` | Caché `_ANIMATED_KEYS` con `animateOnceKey` en `useCountUpV2.js` / `AnimatedNumberV2.jsx`, y `chartAnimationsV2.js` con `$v2InitialAnimDone` + `transitions.active.animation.duration = 0` + `useMemo` para evitar reinicio de gráficas en hover. |
| F10-5 | Pruebas/Build | Completado | `f10_pruebas_back.txt`, `f10_pruebas_front.txt` | Backend `pytest`: **119 passed, 0 failed**. Frontend `vitest`: **25/25 test files passed** y `vite build` limpio (`3.06 s`). Contenedores `api` y `web` reconstruidos (`9/9` Up/healthy). |
| F10-6 | Visual/Cierre | Completado | `f10_verificacion_visual.md` | Verificación en `http://localhost:5173` (`1280×800`) en **modo claro y oscuro**: `0` errores JS, `0` errores de sesión/cookies `401`/`403`, `0` duplicación al navegar `Paso 2 ↔ Paso 3` (`Casos en la selección = 3.780` estable), modal con ablación y hover de gráficas estable sin reinicio. |
