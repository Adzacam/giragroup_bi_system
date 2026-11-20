# CIERRE F5V — 2026-11-19

Rama / commits: `beto-integracion` (`84cd352` código y pruebas + commit de cierre `docs(f5c,f5v)`). Se ejecutó integrada con `PLAN_F5C.md`. No se tocaron ni commitearon `backend/routers/powerbi.py`, `docs/cierres/PLAN_FRONT_V2.md`, `docs/cierres/CIERRE_FRONT_V2.md` ni `uploads/otras_versiones/`.

## Hecho
- **V-1 (Métricas del Modelo BETO):** `BetoMetricasModal.jsx` renombrado a «Métricas del Modelo BETO», con Precisión `97,29 %` / Recall `98,63 %` (estricto) y `98,84 %` / `100 %` (relajado), cifras animadas con `AnimatedNumberV2`, curva de 3 épocas con `react-chartjs-2` + `withChartAnimationsV2` / `ChartRevealV2` (época 2 marcada «Mejor»), celda `PER_ESTUDIANTE → PROGRAMA` resaltada y soporte `prefers-reduced-motion`. Prueba `w9MetricasModelo.test.jsx` ampliada y en verde.
- **V-2 (Ex-paso ② en Lectura):** `TextoPreparadoTab.jsx` incorpora las 3 tarjetas KPI («Registros preparados», «Campos por fila, máximo», «Filas con observaciones») mediante el hook común `useResumenPreparacion.js`, aviso de observaciones y botones de navegación. Eliminados `PlainTextTransformationView.jsx` huérfano y su entrada en `routeDataPrefetcherV2.js`.
- **V-3 (Claridad para el usuario, D1 y D3):** Nota bajo «En revisión» explicando la diferencia frente a los casos del paso ③; «Procesar archivos (N)» y «Vista previa»; entrada deslizante en `PipelineTelemetryDrawer.jsx` respetando `reduced-motion`; historial en 3 pasos (① Carga ② Lectura de BETO ③ Revisión) manteniendo «Lectura de BETO».
- **V-4 (Bandeja y telemetría backend):** `revision_formularios.py` pide campos de identidad (no convenio) para casos de cédula; `/review-tray/grupos` distingue motivos por archivo/tabla/tipo sin alterar agrupación ni conteos (±0); `maestros.py` lee la versión de PyTorch desde `f1_training_info.json`. Evidencia: `docs/mediciones/f5v_bandeja.json`, `tests/f5v/test_bandeja_v4.py`.
- **V-5 (Diagnóstico `NOMBRE DEL PROGRAMA`):** Comparación de 20 filas de `TBL_INSCRITOS.xlsx` frente a `staging_registros_crudos.texto_plano` en `beto_pg_tmpfs`. Evidencia: `docs/mediciones/f5v_nombre_programa.json`.
- **V-7 (NER visible con `origen_confianza`):** `dataops_privacy.py` ampliado con `confianza`, `origen_confianza` y `detalleConfianza` sin exponer PII (`tests/f5v/test_privacidad_confianza.py`); `BetoReadingFlowView.jsx` muestra etiqueta del modelo, origen en lenguaje llano y barras de confianza.
- **V-8 (Absorbida en C-1):** Diagnóstico columna × entidad en los 10 libros (`docs/mediciones/f5c_columnas_por_entidad.json`, `docs/mediciones/f5v_ner_origen.json`).
- **V-9 (Borrado del lote vacío #2, D2):** Previo `pg_dump` verificado (`backups/f5v_pre_borrado.dump`, 654 líneas `pg_restore --list`), eliminado el lote `#2` (`docs_vivos=0`) con delta de hechos `0`. Evidencia: `docs/mediciones/f5v_borrado_lote2.json`.
- **V-6 (Verificación en navegador V1 y `/v2/dataops/*`):** Recorrido headless con Edge + CDP sobre Carga, Lectura (`#35` y `#36`), modal BETO, Texto preparado, NER visible en lote `#36` (`TBL_INSCRITOS` sin docente-asesor y con programa correcto) y Revisión: **0 errores de consola y 0 excepciones**. Evidencia: `docs/mediciones/f5v_verificacion_front.json`.

## Pruebas y despliegue
- `pytest` completo en worktree limpio (`84cd352`): **943 colectadas, 924 passed, 0 failed, 12 skipped, 7 xfailed**, cobertura **72,69 %** (`docs/mediciones/f5c_pruebas.json`).
- `vitest`: **16 archivos, 87/87 passed**; `vite build`: **2.035 módulos, 0 errores**.
- Rebuild de `api` y `web` + reinicio de `giragroup_gateway`: `/health` **200**.
