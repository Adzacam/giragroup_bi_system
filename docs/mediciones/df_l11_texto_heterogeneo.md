# Verificación DF-L11 — Texto heterogéneo admitido

- Contrato documentado en `docs/fuentes/CONTRATO_FUENTES.md`.
- Fixtures sintéticas creadas en `tests/fixtures/fuentes_sinteticas/`:
  - `texto_libre_largo.csv`
  - `hoja_sin_cabecera.csv`
  - `columnas_otro_orden.csv`
- Comportamiento verificado: `extract_entities_from_line` procesa texto narrativo largo, hojas sin cabecera y columnas reordenadas sin excepciones y deriva filas sin estructura/identidad a revisión humana (`0` hechos inventados).
