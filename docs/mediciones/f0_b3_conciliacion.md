# F0 B-3 — conciliación 503/510

La suma 503 procede de una matriz histórica incompleta; el gold contiene 510 entidades.

`scripts/generar_graficos_3_1_3_3.py` (asignación `cm_abs`, líneas 32–37) fija una matriz 4×4 cuyas filas suman 150 módulos, 50 docentes, 130 estudiantes y 173 programas: **503**. El soporte completo de programas es 180; faltan **7** en esa fila. La matriz no representa toda la población gold. Su normalización por suma de fila, además, oculta esa cobertura incompleta.

La inspección Git acotada encontró una única versión registrada del gold: 180 líneas y 510 spans. Su contenido JSON coincide con el actual; la diferencia de hash bruto corresponde a finales de línea, comprobada mediante igualdad de registros. Por tanto, no hay evidencia de un gold histórico de 503 entidades.

La conciliación por definición y suma queda resuelta. La trazabilidad histórica por ID permanece parcial: la matriz está escrita a mano y no guarda IDs ni huella de predicciones originales. Los siete FN de programa de la corrida F0 C son los IDs 26, 40, 111, 128, 132, 146 y 177, pero **no se afirma que sean los siete casos históricos**. En F0 todos tienen predicciones de programa parciales o fragmentadas que se solapan; clasificarlos como siete salidas completamente O sería incorrecto.

Hashes, commit, líneas, matriz, soporte y spans por ID: [f0_b3_conciliacion_git.json](f0_b3_conciliacion_git.json). Conteos: [f0_b3_conteos.json](f0_b3_conteos.json).

Las seis filas A/B/C × estricto/relajado conservan matching 1:1. El estricto usa IOB2 explícito; el reporte heredado usa seqeval por defecto y se conserva separado. [Resultados](f0_b3_ablacion.json), [CSV](f0_b3_ablacion.csv), [predicciones sin texto](f0_b3_predicciones.json), [procedencia](f0_b3_procedencia.json).

La inferencia inicial invalidada está conservada en [f0_b3_invalidada/README.md](f0_b3_invalidada/README.md). La reinferencia válida fijó hashes antes de inferir y ligó posteriormente las predicciones; sus hashes y seis conteos se verificaron nuevamente. No se ejecutó inferencia en esta auditoría ni se modificó el gráfico final; las figuras corresponden a F4.
