# Propuesta de corrección histórica — loop 6

Estado: **preparada, sin aplicar**. Auditoría del 12 de noviembre de 2026. El cambio de cálculo del KPI 06 ya fue confirmado por el usuario y aplicado; esta propuesta trata por separado las anomalías históricas.

## A. Edades sin respaldo: 193 filas del archivo de admisiones

- El documento 19 contiene 15.196 filas de origen. En 193 filas, «EDAD L» vale 127 y no se puede interpretar la fecha de nacimiento. No son 193 personas identificadas: son filas del archivo.
- Los documentos 12 y 19 tienen la misma huella de archivo. Se tratará una sola fuente; no se contarán sus copias como personas distintas.
- **Cambio propuesto:** generar una copia del archivo para corrección, con «EDAD L» vacía en esas 193 filas y una observación que solicite confirmar el nacimiento. Conservar los valores 127 en el original y en el registro de cambios. No deducir una edad a partir de la fecha de inscripción.
- No se actualizará `dim_estudiante.edad`: actualmente las 14.079 personas activas carecen de edad guardada. Tampoco se actualizarán sus fechas de nacimiento o identidades.
- El manifiesto JSON adjunto identifica cada fila por documento, bloque, posición y huella; no incluye nombres, cédulas ni fechas de nacimiento. Son referencias a la serialización de staging: antes de editar una hoja se comprobará la correspondencia con el archivo, sin asumir que la posición serializada es su número de fila Excel.
- Resultado esperado: 193 celdas vacías en la copia de trabajo, 193 observaciones; originales, número de filas e indicadores sin cambios. No subir ni consolidar la copia automáticamente.

## B. Dos módulos sin nombre identificable

| ID conservado | Nombre actual | Nombre propuesto | Código actual → propuesto | Vínculos conservados |
|---|---|---|---|---|
| 4937 | `.` | Programa por identificar (4937) | `MOD-GEN` → sin código | Marketing 29915 y 30613: dos inscripciones cada uno |
| 4957 | `......` | Programa por identificar (4957) | `MOD-GEN` → sin código | Marketing 30276: dos inscripciones |

**Cambio propuesto:** actualizar únicamente el nombre y retirar el código genérico de estos dos módulos. Conservar sus identificadores y las seis inscripciones de los tres agregados. No fusionarlos entre sí ni asignarlos a un programa conocido sin evidencia. Programa e institución se conservan.

Resultado esperado: dos actualizaciones de referencia; cero altas, bajas o movimientos de hechos; mismas seis inscripciones vinculadas. La etiqueta indica que queda pendiente identificar el programa real.

## C. Fecha de inicio inconsistente del convenio 25

- Documento 7, convenio 25: gestión 2024, inicio **2034-01-12**, fin **2024-03-02**; ya está marcado para revisión.
- **Cambio propuesto:** dejar `fecha_inicio` e `id_tiempo` sin dato, conservar gestión 2024, fecha de fin, montos, inscritos, módulo e institución. Mantener `requiere_revision=true` y el motivo «FECHA_INICIO_PENDIENTE: confirmar contra el convenio original; fecha recibida 2034-01-12».
- La fecha recibida se preservará en el original y la auditoría. No se sustituirá por 2024-01-12, porque ese año sería una inferencia.
- No borrar la fecha 2034 de la dimensión calendario: una fecha de calendario no es por sí misma un error. La corrección actúa sobre su vínculo con este convenio.
- Resultado esperado: un convenio actualizado y pendiente; ninguna baja, ningún cambio de importe o inscritos. El KPI 22 usa la gestión del convenio y conserva su conteo de 2024. Las consultas por fecha de inicio dejarán de situarlo en 2034.

## D. Inscripciones históricas: reconstrucción antes de reemplazar

Marketing conserva 15.257 agregados y 45.568 inscripciones. El registro de filas cargadas acredita 15.196 filas del documento 12. El documento 19 es otra referencia al mismo archivo. La tabla de marketing no tiene vínculo documental por agregado; estos números no permiten deducir cuántas inscripciones se duplicaron ni dónde.

**Trabajo propuesto:** reconstruir la fuente única en una base aislada, con clave de archivo, hoja y fila; producir una comparación por programa y período. Presentar el resultado antes de proponer cualquier reemplazo. No dividir los contadores entre dos o tres, ni restar la cantidad de filas del archivo. Esta propuesta no autoriza reemplazar los agregados reales.

## Aplicación y reversión

Para B y C: guardar una copia de las filas afectadas, verificar que los valores actuales coincidan con el manifiesto y actualizar en una transacción; si cambiaron, detenerse. Registrar antes/después y usuario en auditoría. Comprobar identificadores, vínculos y sumas antes de confirmar. La reversión restaura exactamente los campos respaldados. Para A, entregar una copia independiente y su registro de cambios, conservando intacto el archivo original.

La aprobación puede ser por apartado. **A, B y C no se han ejecutado. D no implica reemplazo de datos reales.** El manifiesto reproducible está en [propuesta-integridad-loop6.json](propuesta-integridad-loop6.json), generado mediante `python -m scripts.propuesta_integridad_loop6` en una transacción de solo lectura.
