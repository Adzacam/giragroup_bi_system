# Salidas operativas

Conservar aquí `sprint2_documentos.jsonl`: lo usa el pipeline y `tests/sprint3/test_formatter_gira40.py`.
También se conservan `sprint3_entidades_procesadas.jsonl` (entrada de jobs),
`inconsistencias_sprint3.jsonl`, `sprint3_fact_persistidos.jsonl` y `telemetria_ner.jsonl`.
Son datos operativos/regenerables; no son archivos huérfanos.

`backups/` no se tocó. `lote1387_archivos/` se conserva por su posible uso de reproducción.
`test_gold_revision.csv` se conserva como DUDOSO: no se elimina ni archiva sólo por falta de referencias estáticas.
Los renders/exportaciones antiguos están en `_archivo/output/`; las fuentes SVG en `docs/figuras_src/`.
Las nuevas salidas de scripts históricos se generan en subcarpetas de output, sin sobrescribir el archivo histórico.
