# F0 A4 — contrato de revisión humana

Este contrato prepara el soporte. No contiene decisiones ni resultados F0 y no usa calentamientos como población.

El paquete solo puede sellarse cuando existen las 12 corridas válidas a3/a123, ambas cachés y repeticiones 1–3, con el mismo lote, árbol y modelo. Puede sellarse antes de terminar a2w; el cierre conserva el orden del plan.

```powershell
.venv/Scripts/python.exe scripts/analizar_f0_resultados.py --sellar-top1
```

Este comando verifica únicamente las fuentes a3/a123. La identidad del caso usa archivo, hoja/fila cuando están disponibles, rol y contexto privado completo; excluye motivo e IDs transitorios de base. Conserva el número de filas por corrida y el número de contextos únicos. Filas indistinguibles sin un localizador estable provocan error; no se fusionan silenciosamente. Dos homónimos con distinto CI/contexto permanecen separados. El muestreo es censo si N≤100 o muestra de 100 con semilla 42 si N>100.

Archivos sellados:

- `output/backups/f0_lote/revision_ciega/final/casos.json`: único paquete que se muestra al revisor. Candidatos en orden independiente; sin ranking ni puntuaciones BETO.
- `output/backups/f0_lote/revision_ciega/final/rankings_privados_no_mostrar.json`: referencia inmutable que no debe mostrarse antes de la decisión.
- `docs/mediciones/f0_top1_paquete_sellado.json`: hashes, fecha del sello, identidad y cobertura de fuentes.
- `docs/mediciones/f0_top1_decisiones_plantilla.csv`: únicamente encabezados; no genera etiquetas.

Un nuevo intento con material idéntico es idempotente. Si cambia cualquier miembro sellado, falla antes de sobrescribirlo. No se solicita revisión mientras la población esté incompleta.

El CSV humano debe contener:

| Campo | Contrato |
|---|---|
| `case_id` | ID opaco del paquete ciego; una única decisión por caso. |
| `decision_kind` | `choose`, `reject_all`, `no_candidate`, `insufficient_information` o `exclude`. |
| `candidate_id` | ID opaco existente entre las opciones; solo para `choose`. |
| `reviewer_id` | Identificador opaco, sin nombre/correo; letras, números, guion o guion bajo. |
| `decision_timestamp` | ISO 8601 con zona; no anterior al sello. |
| `blind_package_sha256` | Hash exacto del paquete mostrado. |
| `blinded_before_decision` | Declaración explícita `true` de decisión previa a ver ranking/puntuaciones. |
| `exclusion_reason` | Obligatorio para rechazo, sin candidato o exclusión; vacío para elección válida. |

Después de recibir decisiones reales:

```powershell
.venv/Scripts/python.exe scripts/f0_revision_humana.py --package output/backups/f0_lote/revision_ciega/final/casos.json --rankings output/backups/f0_lote/revision_ciega/final/rankings_privados_no_mostrar.json --manifest docs/mediciones/f0_top1_paquete_sellado.json --decisions RUTA_CSV_HUMANO --output docs/mediciones/f0_top1_resumen.json
```

La importación valida los hashes sellados, IDs, duplicados, candidato, revisor, fecha, ceguera declarada y motivos. No prueba por sí sola el comportamiento humano: la procedencia se basa en la declaración del revisor ligada al paquete.

Top-1 se calcula por configuración sobre decisiones válidas, con coincidencias/N, cobertura de muestra y población, rechazos y exclusiones explícitas. Cachés y repeticiones no multiplican decisiones humanas. Si cambia el top-1 o el conjunto de candidatos entre réplicas/cachés de un mismo caso/configuración, se exige revisar la evidencia por corrida antes de agregar. Una elección del conjunto ciego ausente en una configuración se conserva como exclusión motivada para esa configuración. N=0 produce `null` y `N/D`, nunca 0 %.

Volver a preparar el mismo paquete no borra decisiones ya importadas. A3 mantiene sus etiquetas automáticas como sugerencias, no revisión manual o humana completada.

Limitación comprobada en el humo de formato a3: algunos casos del loader guardan solo el nombre y las sugerencias, sin raw_line, CI, registro_origen_id ni fila. El tooling conserva todos los campos privados disponibles y marca `original_text_only_no_raw_source_link`; no inventa un vínculo por coincidencia de nombre. El número de casos guardados en bandeja no representa el número de filas originales, que el propio staging puede haber agrupado. Si el contexto no distingue candidatos, el revisor usa `insufficient_information` con motivo: se conserva en cobertura y se excluye explícitamente del denominador top-1. La falta de trazabilidad debe informarse a Lean; no se cambia dw_loader ni el esquema en F0.
