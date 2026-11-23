# CIERRE BETO_ACTIVO — 2026-11-23
Rama / commit: beto-integracion (base 649c5cd + fix revisión)
Hecho (máx. 10 líneas):
- BA-L0: Línea base a0 medida sobre lote 1 (78.027 filas, 268.091 entidades, 0 BETO, 1.220 casos en revisión, 1.515,85 s) en `ba_l0_linea_base.csv`.
- BA-L1b: Muestra de 100 entidades REGEX evaluada (`ba_l1b_regex.csv`): 88 eran el placeholder `CI_NO_PROVISTO`; excluyéndolo en `_calcular_resumen_cascada`, la precisión real REGEX es 100 % (12/12).
- BA-L1 + BA-L2: Medición A/B (a0 vs a3, 3 corridas caché vacía/llena en `beto_pg_tmpfs`) sobre lote 1.387 y gold standard: F1 = 0,9714 (≥ 0,85), 982/986 acuerdos QC, 0 sobrescrituras A/B, 0 perfiles creados por BETO; decisión DB1+DB2 registrada en `ba_l2_decision_flags.json`.
- BA-L3: Activado a3 por defecto en `pipeline/config.py` y `docker-compose.yml`; nuevo ruteo en `consolidacion.py` (`< 0,85`, `DESACUERDO_REGLA_BETO` o `RELACION_INCOHERENTE` → bandeja sin insertar; prioridad MEDIA [0,60; 0,85) / ALTA < 0,60).
- BA-L6: Validación configurable de relaciones (a)–(f) en `validacion_relaciones.py` (`cat_regla_relacion`, `nro_modulo` en `cat_modulo`, `nombre_modulo` en `dim_modulo`) integrada antes del INSERT al DW; 0 inserciones inválidas (`ba_l6_relaciones.csv`).
- BA-L4: Pantalla ② honesta (`lectura.py` + `BetoCascadaResumen.jsx`) con las 3 métricas separadas y estado de flags; bandeja ③ (`ReviewActionRenderer.jsx`, `CasoDetallePanel.jsx`, `HumanReviewFlowView.jsx`, `revision_acciones_descriptor.py`, `motivosBandeja.js`) con probabilidad BETO, prioridad (`ALTA`/`MEDIA`), detalle de regla y acciones para `DESACUERDO_REGLA_BETO` y `RELACION_INCOHERENTE`.
- BA-L5: Coherencia entre sistema vivo y script de evaluación (`ba_l5_coherencia.json`, diferencia 0 en etapa BETO).
No hecho y por qué:
- Capturas visuales en navegador vivo de `ba_l4_capturas/` no generadas por Playwright en esta sesión (verificado mediante `vite build` y tests de componente `vitest`).
Invariantes cambiados: no (cascada, umbrales 0,92/90/85/80, bandas 0,85/0,60, catálogo sin docentes/estudiantes, 128 tokens y 51 tablas DW intactos; cambia solo la semántica operativa de la banda [0,60; 0,85) que pasa a bandeja sin insertar según DB1+DB2).
Pruebas: 122 passed, 1 skipped (pytest `tests/beto_activo/`, `tests/f5c/`, `tests/dataops_flujo/`, `tests/sprint3/test_beto_*.py`, `tests/sprint5/test_beto_integracion_flujo.py`, `tests/adw/test_l7_pipeline.py`) · 66 passed en 15 archivos (vitest `frontend/src/modules/dataops/__tests__/`) · `vite build` exitoso.
Servicios reconstruidos + estado de docker compose ps: `api` y `web` reconstruidos y arriba; los 9 servicios en `Up` / `healthy`.
Cambios de esquema o API: `resumen_cascada` en `GET /api/v1/dataops/lote/{id_lote}/resumen` añade `lineas_confianza_beto`, `acuerdo_qc_comparadas`, `acuerdo_qc_acuerdos`, `acuerdo_qc_pct` y `flags`; `GET /api/v1/dataops/review-tray` añade `prioridad`, `regla_relacion`, `valor_relacion` y `detalle_relacion`.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- F1 a3 sobre gold standard | 0,9714 | `docs/mediciones/ba_l1_ab.json`
- Tiempo ciclo a3 lote 1.387 (caché vacía / llena) | 86,013 s / 0,757 s | `docs/mediciones/ba_l1_ab.json`
- Acuerdos QC regla–BETO (a3 lote 1.387) | 982 / 986 (99,6 %) | `docs/mediciones/ba_l1_ab.json`
- Precisión REGEX muestra 100 (con / sin `CI_NO_PROVISTO`) | 12,0 % / 100,0 % | `docs/mediciones/ba_l1b_regex.csv`
- Filas insertadas con índice < 0,85 o relación inválida | 0 / 0 | `docs/mediciones/ba_l3_aplicado.csv`, `docs/mediciones/ba_l6_relaciones.csv`
Impacto en el documento (sección o tabla):
- Cap. III, Sec. 3.4: nueva semántica de banda [0,60; 0,85) → bandeja sin insertar con prioridad MEDIA; < 0,60 → prioridad ALTA.
- Fuente de verdad (línea 10) y A-15: flags a3 activos por defecto en sistema vivo y scripts.
Riesgos abiertos:
- El conteo de entidades resueltas por BETO sobre el lote completo de 78.027 filas con a3 en vivo queda listo para medirse en la recarga de `PLAN_ACEPTACION_FLUJO.md`.
Pendiente para el chat 4:
- Actualizar Gráfico 4.2 tras la recarga completa con a3 activo.
