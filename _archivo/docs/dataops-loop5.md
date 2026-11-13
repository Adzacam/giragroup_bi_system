# DataOps — loop 5: catálogo de referencia y bitácora

Alcance indicado por el usuario el 11 de noviembre de 2026: el catálogo no debe mostrar estudiantes ni docentes. Se retiraron sus pestañas, consultas y controles de mantenimiento de las vistas de catálogo de DataOps y Ajustes. Los registros de personas necesarios para procesamiento, revisión y consultas académicas se conservan.

## Catálogo

- Una consulta de DataOps permite exclusivamente módulos e instituciones. Devuelve cinco registros por página, totales reales y búsqueda en el servidor; rechaza los tipos de personas. Las vistas de DataOps y Ajustes comparten el mismo componente de referencia.
- Las instituciones proceden de la tabla institucional existente en la base operativa. No se deducen de nombres de módulos ni se añaden instituciones, estados o identificadores de ejemplo. La revisión real permitió corregir la consulta que inicialmente apuntaba a otra base sin esa tabla.
- Ajustes conserva la consulta de conceptos financieros, con cinco filas por página, sin la pestaña ni la consulta de docentes.
- Se eliminan los sustitutos visuales «Pregrado», «General», «MOD-N/A» y «Activo» fijo. Un campo no informado se muestra como «Sin dato». Los valores históricos que ya están guardados se mantienen para la revisión de integridad.
- Los identificadores numéricos y contactos mal clasificados en campos de referencia se protegen al responder. Esto no reclasifica ni reescribe los registros originales.
- El alta de módulos exige nombre e institución, valida longitudes y conserva ausencias de programa o código sin generar relleno. Una reserva transaccional en PostgreSQL serializa altas idénticas y evita duplicados.
- Se recuperan los botones de alta y actualización corrigiendo la propiedad del encabezado. Los botones compartidos indican carga, guardado o eliminación, y un bloqueo evita el doble envío. La baja presenta una confirmación Sileo con el registro concreto.
- La baja de un módulo con referencias se rechaza para conservar su historial. Los módulos sin referencias pueden eliminarse. Las altas y bajas guardan auditoría, invalidan consultas y notifican a Administrador y Auditor de Calidad; la campana se actualiza al guardar.
- Las instituciones son de consulta: no se ofrece un alta que el backend no implementa.

## Bitácora

- Un documento inexistente devuelve 404; no abre el último archivo de otro lote.
- Eventos y mapeos de columnas se paginan de cinco en cinco, con totales independientes. Los mapeos provienen del evento de normalización registrado; una primera fila de datos no se usa para inventar una matriz de auditoría.
- Se eliminan firmas binarias simuladas, reglas fijas, mapas de columnas de ejemplo, SQL generado, verificaciones «PASS», latencia de 185 ms y métricas de calidad o confianza deducidas sin evidencia.
- Se muestran la etapa, nivel, fecha y duración de cada evento real. Los mensajes internos históricos pueden contener parámetros SQL o información personal y se conservan en el servidor; no se publican esos mensajes ni muestras de valores.
- La huella SHA-256, documento, lote, fecha y otros datos registrados quedan en «Detalles técnicos», plegado. Una huella ausente no se sustituye por una huella de ejemplo ni por «Verificada».
- La descarga Markdown se genera en el backend e incluye todos los eventos y columnas registrados del documento, no solo la página visible. Se comprobó su descarga desde el navegador.
- Bitácora y formulario usan la capa de ventanas del documento, por encima de la cabecera. El fondo no se desplaza mientras están abiertos y Escape permite cerrarlos. Se mantienen colores, tipografía y componentes del sistema en claro y oscuro.
- Se elimina el GET `/entities/unresolved`, sin consumidores, que devolvía toda la bandeja sin paginar y sin la protección actual. Se retiran clientes y estados de interfaz que dejaron de utilizarse.

## Verificación

- Línea base: 587 pruebas aprobadas. Suite completa: 604 aprobadas, 11 omitidas y los mismos 7 fallos esperados. Las 17 pruebas nuevas cubren catálogo sin personas, roles, páginas, búsqueda global, protección de campos mal clasificados, altas sin relleno, duplicados, bajas con vínculos, bitácora y exportación sin muestras personales, datos ausentes y documentos inexistentes.
- Compilación de producción del frontend correcta, incluida la corrección visual posterior de las ventanas. No se modificó el backend después de ejecutar la suite completa.
- Medición de lectura real: módulos, cinco de 4.211 registros, 867 bytes y aproximadamente 0,025 s; instituciones, cuatro registros reales, 505 bytes y aproximadamente 0,005 s.
- Navegador con cuenta Administrador: módulos en páginas 1 y 2, instituciones, catálogos de Ajustes sin personas, dieciséis conceptos financieros en páginas de cinco, formulario sin enviar, bitácora de un documento del lote 2 con diez eventos y treinta y siete columnas, paginación de la matriz, huella plegada, descarga, Escape y ambos temas. Se restauró el modo claro y la búsqueda quedó vacía.
- No se cargaron archivos ni se realizaron altas, bajas, resoluciones o consolidaciones sobre datos reales. Las escrituras se comprobaron en bases aisladas. No había tareas activas al actualizar los contenedores locales.

## Pendientes

- Permanecen para el loop 6 los módulos llamados «.» o «......», códigos genéricos ya guardados, cargos o identificadores mal clasificados y las observaciones previas de edades, fechas, catálogo e integridad de conteos.
- La bitácora pública muestra los eventos y campos estructurados registrados, no una copia de los mensajes técnicos internos. Una revisión técnica de esos mensajes requiere acceso al servidor.
