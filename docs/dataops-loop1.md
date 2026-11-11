# DataOps — loop 1: carga e historial

Cambios confirmados por el usuario el 11 de noviembre de 2026.

## Resultado

- Se eliminan los controles sin efecto de confianza y anonimización. La pantalla muestra el 85 % fijo y explica la protección del servidor.
- El historial consulta un endpoint paginado por lote: cinco filas por página, sin repetir cada lote por sus archivos. Muestra estado, fecha, origen y conteos reales.
- Las acciones dependen del estado. Los lotes consolidados abren el resumen de solo lectura; no se presentan controles de edición mientras se comprueba el contexto.
- La bitácora exige un documento real de la fila seleccionada. Se retira el identificador 1 usado como sustituto y se comunica el error de consulta.
- La carga exige seleccionar escala de notas en actas y Moodle, también en el servidor. Los duplicados se detectan por contenido e institución, incluso si el periodo se reconoció automáticamente.
- Los archivos que fallan no se presentan como exitosos. Se conservan para corregirlos y se contabilizan también los duplicados.
- Se bloquean envíos y reintentos simultáneos. Solo pueden eliminarse desde el historial las entradas fallidas sin documentos procesados.
- La ingesta deja de descargar el texto completo para mostrar una pequeña vista previa. Presenta metadatos del archivo y dirige la revisión de contenido a sus pasos correspondientes.
- Se retiran estimaciones inventadas de filas y tamaños, y la confirmación de huella que se mostraba antes de calcularla.
- Los avisos de tareas usan Sileo y un identificador propio por aviso. El servidor persiste resultados para Administrador y Auditor; la campana los vuelve a consultar. También se registra el error de tareas interrumpidas sin latido.
- Títulos por paso, roles legibles, cifra del catálogo compartida y colores del tema existente.

## Verificación

- Línea base: 519 pruebas aprobadas, 11 omitidas y 7 fallos esperados.
- Suite completa final: 533 pruebas aprobadas, 11 omitidas y los mismos 7 fallos esperados. Sin regresiones en las pruebas ejecutadas.
- Pruebas nuevas aisladas con SQLite y directorios temporales: CSV y Excel válidos, escala obligatoria, formatos inválidos, límites de tamaño y cantidad, duplicados, historial de varios archivos, estado consolidado de evaluación docente, eliminación protegida, reintentos y tareas interrumpidas.
- Compilación de producción del frontend sin errores.
- Navegador: ingesta en claro y oscuro, historial real, acciones de lotes consolidados, resumen de solo lectura y aviso visible en la campana.
- Las cargas de prueba se ejecutaron en el entorno aislado de pruebas. No se subió un lote de prueba a la base operativa.

## Observaciones para los loops siguientes

- Loop 2: sigue pendiente decidir qué datos personales, además de la cédula, se enmascaran. La consulta completa de texto conserva su contrato; su paginación general corresponde a ese loop.
- Loop 3: revisar los GET que pueden iniciar una lectura y las tareas antiguas asociadas a lotes ya consolidados.
- Loop 5: la bitácora conserva mapeos, firmas de formato y otros detalles fijos. En este loop solo se corrige la selección del documento, no todo el contenido del componente.
- Acceso: se observaron los textos dañados «30 d�as» y «??», y varios detalles técnicos que conviene simplificar. Pendiente de confirmar su revisión fuera de la ingesta.
- La verificación visual se realizó con Administrador; el destinatario Auditor se comprobó en la persistencia del backend, sin iniciar una segunda sesión.
