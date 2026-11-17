# F3U-B — resumen para Lean

## Cobertura por libro completo

| Archivo | Origen | Leídas | Con registros | Bandeja | Ruido | Sin explicar | Delta fuente* |
|---|---:|---:|---:|---:|---:|---:|---:|
| TBL_INSCRITOS.xlsx | 15.196 | 15.196 | 15.191 | 5 | 0 | 0 | -2 |
| BD Cobranzas.xlsx | 15.964 | 16.034 | 15.472 | 2 | 560 | 0 | -70 |
| BD Techos.xlsx | 207 | 207 | 207 | 0 | 0 | 0 | 0 |
| EJECUTADO VS META.xlsx | 36 | 36 | 24 | 0 | 12 | 0 | 0 |
| BD Egresos.xlsx | 1.409 | 1.409 | 1.397 | 0 | 12 | 0 | 0 |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | 6.768 | 8.216 | 0 | 0 | 8.216 | 0 | -1.448 |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | 19.062 | 19.119 | 18.991 | 0 | 128 | 0 | -323 |
| Evaluación Docente y Unifranz.xlsx | 3.813 | 27.189 | 12.301 | 4.306 | 10.582 | 0 | -23.732 |
| Experiencia Docente 2.0.xlsx | 16.629 | 17.695 | 16.629 | 0 | 1.066 | 0 | -1.475 |
| Base centralizada Académica ARCA (1).xlsx | 11.454 | 11.456 | 10.296 | 325 | 835 | 0 | -2 |

\* Delta = origen_slice − leídas − logs SUBTOTAL. Los siete deltas distintos de cero requieren revisión; la definición y el detalle están en [f3ub_defectos.md](f3ub_defectos.md). Todas las líneas leídas clasifican (`sin_explicar=0`), pero el script no produce balance del origen por fila, destinos por hoja ni fechas por hoja.

## Persistencia y diseño B

Los 10/10 documentos terminaron `COMPLETADA`. Conteos finales de la copia: 25.108 rendimiento académico; 10.719 situación financiera; 715.217 evaluación docente; 10.432 marketing; 95 rentabilidad; 1.371 costo de programa; 206 techo/convenio; 0 forecast; 0 cobranzas proyectadas; 68 staging; 14.359 no resueltos; 22.746 inconsistencias; 30.366 `carga_fila_origen`. Evidencia, rangos de fechas y dump: [f3ub_completo.json](f3ub_completo.json), [f3ub_fechas_por_hecho.json](f3ub_fechas_por_hecho.json), `output/f3ub/f3u_completo.dump` (fuera de Git).

El diseño de opción B está en [f3ub_planificacion_diseno.md](f3ub_planificacion_diseno.md): `fact_planificacion_programa`, vista mensual y KPI-23. La comparación de metas, estados, valores manuales y pauta está en [f3ub_planificacion_adenda.json](f3ub_planificacion_adenda.json). En breve: los objetivos de `Informe Gestión` no cuadran mes a mes con `EJECUTADO VS META`; las metas financieras existentes se conservan como autoridad para KPI-02/03/13/14 y la planificación se mantiene separada. KPI-23 requiere decisión de meta por Lean; `Inicio Confirmado`, `En curso` y `Finalizo` cuentan como iniciados; pauta no es KPI ni ingreso.

## Decisiones pendientes

1. Para cada diferencia con `requiere_revision`, decidir si se analiza/corrige en F3V o se mantiene como limitación.
2. Confirmar que `EJECUTADO VS META` sigue como autoridad de KPI financieros; metas de Informe Gestión se usan en planificación.
3. Definir meta del KPI-23: 12 aperturas por mes o tasa de inicio respecto del plan.
4. Mantener pendientes F3U citados en `PLAN_F3U_B.md`: huella/cabecera SFV, B-7 (`n=3`) y selección de corridas limpias.
