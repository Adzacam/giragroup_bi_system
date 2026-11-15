**Superado por la declaración de Lean del 2026-11-15**: ver `../resumen.json` y `../a3_etiquetas_rev01.csv` / `../a4_decisiones_rev01.csv`.

# Revisión `rev_01` apartada (no válida como revisión humana)

Los archivos en este directorio corresponden a la revisión `rev_01` registrada el `2026-11-15` y **no son válidos como evidencia de revisión humana** por los siguientes 4 motivos:

1. **`human_label == technical_label` en 90/90:** las 90 filas de A-3 replicaron exactamente la sugerencia técnica automática (`desacuerdo real`) sin criterio independiente verificado.
2. **`label_status` sin transición:** todas las filas permanecieron con `label_status = automatic_suggestion_not_reviewed`.
3. **Temporalidad concentrada en 2 instantes:** todas las etiquetas se registraron en solo 2 marcas de tiempo (`11:46:27` y `12:11:39`), incompatible con una revisión manual independiente de 90 contextos y 7 casos.
4. **Alteración de artefactos sellados de F0:** la importación modificó `docs/mediciones/f0_desacuerdos_muestra.csv` y `docs/mediciones/f0_top1_resumen.json`, que habían sido restaurados/sellados en F0 (`b559292`).

Ninguna cifra de este directorio debe citarse como validación humana.
