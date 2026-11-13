# DataOps — loop 3: lectura de BETO

El usuario confirmó el 11 de noviembre de 2026 dejar la consolidación exclusivamente en el paso ④. Las edades fuera de rango quedan pendientes para el loop 6.

## Cambios

- El paso ③ consulta resultados guardados. Un GET de lectura o resumen no ejecuta BETO, espera inferencia ni crea tareas de análisis.
- Si falta una lectura en un lote abierto, el usuario puede iniciarla expresamente. El POST bloquea el lote y reserva la tarea en la misma transacción; reutiliza una tarea activa o resultados existentes. La ingesta reserva su tarea antes de programar el trabajo en segundo plano.
- Una lectura solo se anuncia como terminada después de guardar sus resultados. Los errores públicos de tareas no incluyen parámetros SQL ni datos personales; se conserva el error interno para diagnóstico.
- Se mantienen Sileo, el seguimiento global de tareas y las notificaciones persistentes por rol existentes. Los botones indican consulta, inicio o revelado en curso y evitan solicitudes duplicadas desde la pantalla.
- La API limita las páginas a cinco filas. Área, condición, entidad y búsqueda se aplican en el servidor antes de paginar, sobre todo el lote o archivo seleccionado. La búsqueda ignora acentos y cambiar filtros reinicia la página.
- El resumen indica su alcance; los filtros afectan la lista. Los índices ausentes se muestran como «Sin dato», sin sustituirlos por porcentajes inventados. Se elimina la métrica F1 fija sin respaldo en esta consulta.
- Los detalles quedan plegados. Se explican los rangos de decisión y las excepciones por reglas; se eliminan los botones y la ventana de consolidación duplicados.
- La protección de datos del loop 2 se comparte con la lectura y también se aplica a cachés antiguas, sin modificar esos archivos. Se ocultan nombres, documentos y contactos en el texto, entidades y explicaciones; se excluyen tokens que permitan reconstruir nombres.
- La cédula se revela únicamente mediante el endpoint auditado existente y permanece en la fila montada. No se ofrece revelar una cédula inexistente.
- El texto original conserva campos públicos rotulados como nombre del programa aunque el modelo los haya confundido con una persona. Las entidades personales siguen protegidas.
- Los lotes cerrados admiten consulta y filtros. Si no tienen una lectura guardada, se informa sin recalcular ni modificar el lote.
- Se conservan tipografía, componentes compartidos y colores de los modos claro y oscuro. La selección de archivo y los filtros se conservan por lote.

## Verificación

- Suite completa final: 566 pruebas aprobadas, 11 omitidas y los mismos 7 fallos esperados anteriores; sin fallos nuevos. Las omitidas requieren una base de readiness configurada.
- Compilación de producción del frontend correcta; distribución actualizada en el contenedor local.
- Pruebas aisladas de paginación 5/5/4, filtros globales, acentos, índices nulos, privacidad de cachés antiguas, documentos ajenos, límites HTTP y roles; GET sin inferencia, reservas reutilizadas, lotes cerrados y fallos al reservar o guardar.
- Navegador con cuenta Administrador: páginas 1–5 y 6–10, búsqueda global con 211 coincidencias, filtros sin resultados, actualización, texto original protegido y modos claro/oscuro. Se restauraron filtros y tema claro.
- Medición de lectura del lote real de 15.196 registros: cinco filas, 19.384 bytes JSON y aproximadamente 0,84 segundos. No se crearon tareas durante las consultas.
- No se cargaron archivos, revelaron cédulas, consolidaron lotes ni ejecutaron análisis sobre datos reales. El inicio, avance y fallo del proceso se verificaron con pruebas aisladas.

## Observaciones pendientes

- Edades fuera de rango: loop 6, según indicación del usuario.
- El lote histórico consultado contiene coincidencias dudosas con el catálogo: por ejemplo, un nivel académico se presenta asociado a un diplomado que difiere del programa del texto original. Se documenta para revisar la integridad y clasificación; este loop no reescribe decisiones históricas.
- El lote 1 está cerrado y no tiene una lectura guardada disponible. Se informa de esta condición sin iniciar otro procesamiento.
- El paso ④ y sus exportaciones requieren su propia revisión; los endpoints antiguos ajenos a esta pantalla conservan su comportamiento.
