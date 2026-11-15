# F1 A-8a — Auditoría e integración de `beto-entrenamiento` (`9888539`)

- **Rama destino:** `beto-integracion` (sobre `2aa5398d917ef503a26bb300cf514ed2ffd1db62`)
- **Rama origen integrada:** `beto-entrenamiento` (`9888539`, worktree `giragroup_beto_wt` intacto)
- **Archivos integrados (18):**
  - Nuevos (11): `.gitattributes`, `docs/auditoria/beto_entrenamiento_endurecimiento.md`, `docs/evidencias/beto_corpus_determinismo.json`, `docs/evidencias/beto_manifiesto.json`, `requirements-lock.txt`, `scripts/beto_metricas.py`, `scripts/beto_reproducir.sh`, `scripts/evaluar_beto_checkpoint.py`, `scripts/generar_manifiesto_beto.py`, `scripts/matriz_confusion_ner.py`, `tests/sprint3/test_beto_entrenamiento_endurecimiento.py`.
  - Actualizados sin conflicto (6): `backend/routers/dataops/maestros.py`, `scripts/ablacion_beto.py`, `scripts/entrenar_beto_robusto.py`, `scripts/finetune_beto_ner.py`, `scripts/generar_graficos_3_1_3_3.py`, `scripts/preparar_corpus_robusto.py`.
  - Combinado preservando B-10 (1): `Makefile` (se mantuvieron `$(TEST_DATABASE_URL)` sin secretos y se añadió el target `beto-reproducir`).
- **Invariantes y defaults:** sin cambios (4 flags `BETO_*` permanecen apagados; `pipeline/semantic/beto_local` vigente sin sustituciones).
- **Verificación:** `tests/sprint3/test_beto_entrenamiento_endurecimiento.py` → **15 passed, 0 failed** (`48,90 s`).
