# Propuesta de corrección: inscripciones triplicadas en la base viva

Estado: **preparada, sin aplicar**. Medición del 12 de noviembre de 2026, solo lectura, comparando `giragroup_db` con `snapshot_dw_20261110_1201`.
El snapshot sigue siendo la fuente de la tesis; esta propuesta corrige la base operativa sin reemplazarlo.

## Qué se midió

| Elemento | Snapshot | Base viva | Diferencia |
|---|---:|---:|---|
| Filas de `fact_marketing` | 8.946 | 15.257 | 6.311 filas nuevas (ids 26692 a 33002) |
| Inscripciones | 15.196 | 45.568 | +30.372 = 16.602 en filas nuevas + 13.770 sumadas a 4.424 filas existentes |
| Filas sin cambio | — | 4.522 | |
| Módulos (`dim_modulo`) | 3.585 | 4.211 | 626 nuevos, con nombres de carrera y código `MOD-GEN` |
| Documentos de origen | 16 | 19 | 17 y 18 repiten `EJECUTADO VS META`; 19 repite `TBL_INSCRITOS` |
| Estudiantes | 14.078 | 14.079 | el id 14780, sin hechos asociados |

- Ningún par (módulo, tiempo) está repetido en ninguna de las dos bases: la duplicación no se ve como filas iguales, sino como filas nuevas con módulos nuevos y como contadores sumados.
- Los 626 módulos nuevos solo los usa `fact_marketing` (4.470 filas); ninguna otra tabla los referencia.
- `fact_rentabilidad` tiene el mismo contenido (108 filas, mismo resumen criptográfico sin el documento); solo cambia el documento al que apuntan 95 filas: del 15 al 18.
- El registro de filas cargadas (`carga_fila_origen`) tiene 15.196 filas del documento 12 y ninguna del 19: la segunda carga no pasó por la protección contra duplicados.

## Cambios propuestos (todos en una transacción, con respaldo y comprobaciones)

1. **Respaldo** de las filas afectadas en el esquema `respaldo_correccion_20261112`.
2. **Restaurar** los contadores de las 4.424 filas de marketing que cambiaron, con los valores del snapshot.
3. **Eliminar** las 6.311 filas nuevas de marketing.
4. **Eliminar** los 626 módulos nuevos, solo si ya no los referencia ninguna tabla.
5. **Eliminar** el estudiante 14780, solo si no tiene hechos asociados.
6. **Reapuntar** las 95 filas de rentabilidad del documento 18 al 15 (contenido idéntico).
7. **No tocar** los documentos 17, 18 y 19, sus registros de auditoría ni el lote 2: son historia. Se anotan como duplicados en el documento de la tesis.

Resultado esperado: 8.946 filas, 15.196 inscripciones (4.737 en 2025), 3.585 módulos, 14.078 estudiantes. KPI-06 sigue siendo N/D. El MAPE sobre la base viva vuelve a 13,89 % en el mismo entorno del snapshot.

## Seguridad y reversión

- Las guardas comprueban que la base conserve exactamente las cifras medidas antes de empezar; si cambió, la transacción se detiene.
- Las comprobaciones finales verifican las sumas esperadas; si alguna falla, la transacción se revierte.
- La reversión completa es restaurar desde el esquema de respaldo.
- El script SQL está en [propuesta-correccion-inscripciones.sql](propuesta-correccion-inscripciones.sql). **No se ha ejecutado.**

## Prevención

La causa es que la consolidación del paso ④ cargó un archivo ya cargado sin consultar el registro de filas. El loop 6 ya unificó la clave del registro; falta una prueba de integración que cargue dos veces el mismo archivo y compruebe que `fact_marketing` no cambia. La validación en una base aislada está en curso (ver `docs/evidencias/`).

## Validación en bases aisladas (12 de noviembre de 2026)

Ninguna de las pruebas tocó `giragroup_db` ni el snapshot (quedaron en 15.257 y 8.946 filas de marketing).

**1. La corrección funciona.** Se ejecutó el script SQL sobre una copia de la base viva (`clon_correccion`): `fact_marketing` quedó con 8.946 filas, 15.196 inscripciones (4.737 en 2025), 3.585 módulos y 14.078 estudiantes. El resumen criptográfico de `fact_marketing` es **idéntico al del snapshot**. Los KPI de 2025 y 2026 coinciden con los del snapshot salvo KPI-06, que pasa a N/D por diseño. El Holt-Winters da MAPE 13,89 %, RMSE 75,03 y AIC 239,56 ([evidencia](evidencias/holtwinters_recalculo_clon_corregido_20261112.json)). Un primer intento falló porque el snapshot es anterior a la migración 014 y no tiene las columnas de captación; la guarda detuvo la transacción sin cambios y el script se corrigió.

**2. Deduplicación.** En un DW reiniciado (`clon_9min`):
- Un mismo archivo con **bytes idénticos** cargado dos veces por `/pipeline/process` **no** suma inscripciones (782 antes y después), pero sí crea un documento de origen nuevo en cada carga (2, 3 y 4 documentos `TBL_INSCRITOS`). Es el mismo patrón de los documentos 17, 18 y 19 de la base viva.
- El mismo contenido exportado de nuevo (bytes distintos, huella distinta) **sí duplica**: 391 inscripciones pasaron a 782 al repetir el ciclo.
- Conclusión: la protección es por huella del archivo, no por contenido. La idempotencia del Cap. III vale solo para archivos byte a byte idénticos.

**3. Tiempo del ciclo de 10 archivos (mes 2026-03, hojas completas) con el DW reiniciado:** 69,13 s de máquina (lectura e ingesta 5,7 s; reglas 5,8 s; BETO 7,9 s; carga al DW 48,8 s) y 95 s de reloj con el arranque. En la segunda pasada, 59,2 s. La bandeja pasó de 0 a 180 casos. El tiempo humano de la revisión no se midió: el simulador `scripts/simular_revision.py` quedó desactualizado frente a la bandeja paginada del loop 4 (falla con `KeyError: 'ids'`). Evidencia: [primera pasada](evidencias/ciclo_9min_dw_reiniciada.json) y [segunda pasada](evidencias/ciclo_9min_dw_reiniciada_segunda_pasada.json).
