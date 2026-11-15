# Revisión humana `rev_01` (F1R2 / R-4)

Revisión declarada por Lean el 2026-11-15: la dictó al chat 2, que la registró en lote. Las marcas de tiempo son de registro, no de revisión.

## Archivos

| Archivo | Qué es | Procedencia |
|---|---|---|
| `a3_etiquetas_rev01.csv` | 90 filas `case_id, technical_label, human_label, reviewer_id` de la muestra de desacuerdos (A-3) | Extraído de `3be4fbe:docs/mediciones/f0_desacuerdos_muestra.csv`. Sin `review_timestamp`. |
| `a4_decisiones_rev01.csv` | 7 decisiones top-1 (A-4), todas `exclude` | Movido sin cambios desde `f1_revision_no_valida/`. sha256 `5ee7b13a…faf`. |
| `resumen.json` | Cifras recalculadas desde los CSV, hashes de F0 y de los nuevos CSV, cruces y procedencia | Generado en R-4. |
| `historial_r1/` | Revisión apartada de R-1 (README con motivos y resumen previo) | Superada por la declaración de Lean. No citar sus cifras como validación. |

Los archivos `docs/mediciones/f0_*` no se modifican en esta carpeta. Sus sha256 están en `resumen.json`.

## Cifras

- A-3: 90/90 `desacuerdo real`. Falsos desacuerdos: 0/90 (0 %).
- A-4: 7/7 `exclude`. Top-1 N/D (0 casos con candidato decidido).
- Cruces: 90/90 `case_id` en la muestra sellada; 7/7 `case_id` de A-4 en `f0_top1_resumen.json`.

## Limitaciones

1. **Sesgo de anclaje en A-3.** La columna `technical_label` estaba visible al revisor. Por eso el 0 % de falsos desacuerdos debe leerse con esta nota.
2. **Marcas de tiempo de registro.** No sirven para medir esfuerzo de revisión ni para el KLM (B-6). Los tiempos de ciclo siguen sin certificar RNF-03 (B-7).
3. **Top-1 N/D.** Las 7 decisiones son `exclude`; no hay cifra top-1 humana.
4. **Declaración, no verificación independiente.** Ningún agente generó, completó ni corrigió estas etiquetas.
