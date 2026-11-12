# DataOps — loop 4: revisión y consolidación

El usuario solicitó continuar con el loop 4 y confirmó mantener las filas de presupuesto confundidas con personas pendientes de revisión manual, excluidas de la aprobación automática en bloque. No se descartaron ni reclasificaron datos reales. Las edades y las coincidencias históricas dudosas con el catálogo siguen pendientes para el loop 6.

## Cambios

- La bandeja consulta resultados guardados. Se elimina la evaluación de BETO y la extracción de entidades al abrirla. El recorrido de casos usa bloques acotados y solo materializa la página solicitada.
- Grupos, casos pendientes e historial de casos resueltos se muestran de cinco en cinco. Búsqueda, área, archivo y grupo se aplican antes de paginar, sobre toda la selección. La búsqueda incluye las definiciones visibles de los motivos, no solo sus códigos.
- Grupos y casos son desplegables. Se eliminan los paneles redundantes, los conteos locales sobre 500 filas, índices inventados de 80/72 %, el guardado ficticio en catálogo y las confirmaciones de éxito optimistas.
- Un lote o documento inexistente devuelve un error: nunca amplía silenciosamente la consulta al resto de los lotes.
- Las claves públicas de los grupos son identificadores derivados; no contienen la cédula ni la clave de agrupación original. Se protege la cédula en los textos, sugerencias, entidades e historial antes de responder. El nombre permanece visible en el paso ④; correos y títulos de programas no se presentan como nombres de estudiantes.
- La exportación CSV se genera en el backend, incluye todos los casos de la selección y protege las cédulas. No depende de las cinco filas de la pantalla ni de una cédula revelada en memoria. Escapa celdas que podrían interpretarse como fórmulas. Se habilita en las vistas de casos, con sus filtros.
- Aprobar, descartar, corregir un grupo, aprobar en bloque y consolidar comparten una espera de diez segundos con Sileo y Deshacer. Solo hay una operación pendiente por pantalla. Salir cancela la espera; nunca adelanta el envío. Durante el envío se bloquean nuevas acciones.
- La consolidación corre en segundo plano con su progreso y notificación persistente por rol. La reserva se realiza dentro de la transacción que bloquea el lote; una segunda petición reutiliza la tarea en curso. La pantalla ofrece un único botón de consolidación.
- Las resoluciones individuales y en bloque comparten validación, guardado y auditoría. Si el guardado falla o devuelve un registro sin incorporar, el caso sigue pendiente. No se guarda una máscara como cédula real; se conservan valores cero.
- El descarte exige motivo. Fechas, notas y cantidades se validan en el servidor. Las correcciones de hechos comprueban sus campos obligatorios y las coincidencias de estudiante y módulo, evitando anunciar cambios que no se aplicaron.
- La revisión avisa a Administrador y Auditor de Calidad, sin nombres ni cédulas en los mensajes de la campana. La aprobación en bloque emite un resumen por rol. Se actualiza la campana al guardar. La consolidación mantiene el seguimiento global de tareas y evita una segunda notificación de finalización duplicada.
- Los lotes cerrados permiten consultar y exportar; no muestran acciones de escritura. El servidor protege las resoluciones, grupos y consolidaciones de esos lotes. El cierre ofrece Iniciar nuevo lote. Los registros de origen se identifican como tales y no se presentan como una cantidad de hechos incorporados.
- Se mantienen componentes, tipografía y colores del sistema en modo claro y oscuro. Los filtros se conservan por lote; los formularios y las cédulas reveladas permanecen en memoria de la fila.

## Verificación

- Línea base del loop anterior: 566 pruebas aprobadas, 11 omitidas y 7 fallos esperados.
- Suite completa: 587 pruebas aprobadas, 11 omitidas y los mismos 7 fallos esperados. Comprobación final de la consulta, privacidad y exclusión de presupuestos: 20 pruebas dirigidas aprobadas.
- Pruebas de API con SQLite aislado: paginación 5/5/4, historial paginado, filtros globales y grupos, privacidad, roles, exportación completa, fórmulas CSV, ausencia de inferencia, reserva reutilizada, errores de carga y correcciones incompletas.
- Pruebas de temporizadores con Node: no envía antes de diez segundos, no duplica el envío y cancelar durante la espera impide la escritura.
- Compilación de producción del frontend correcta. Contenedores locales actualizados sin tareas activas.
- Navegador con cuenta Administrador: lote cerrado, historial de 13 casos, páginas 1–5 y 6–10, desplegable de caso, ausencia de botones de escritura, búsqueda por el motivo visible y aviso Sileo al actualizar.
- Modos claro y oscuro revisados, con selección de pestaña visible. Se restauró el modo claro y la búsqueda quedó vacía.
- Consulta real del historial del lote 2, página 2: cinco casos de trece, 15.248 bytes de JSON y aproximadamente 0,04 segundos. No se crearon tareas durante la lectura.
- No se cargaron archivos, revelaron cédulas, resolvieron casos ni consolidaron lotes reales. Las escrituras y el contador se comprobaron con pruebas aisladas; los lotes disponibles para la revisión visual estaban cerrados.

## Pendientes y límites

- La agrupación recorre los casos existentes para contar y agrupar; la respuesta es paginada, pero todavía no hay un índice SQL de agrupación normalizada. La búsqueda sobre explicaciones protegidas también requiere recorrer el conjunto en bloques.
- El historial de casos resueltos corresponde a los casos de la bandeja guardados. Las resoluciones de hechos que no tienen una fila de bandeja permanecen en su bitácora, no se inventa un historial adicional.
- Las filas de presupuesto se mantienen pendientes y con aprobación como persona bloqueada. Su reclasificación requiere revisar el origen; no se introduce un nombre, cédula o hecho ficticio para sacarlas de la bandeja.
- Integridad de conteos, edades y correspondencias históricas con el catálogo: loop 6. Datos maestros y bitácora técnica: loop 5. Separación completa del router: loop 7.
