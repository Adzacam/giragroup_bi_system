# DataOps — loop 2: texto preparado

El usuario solicitó este loop y confirmó ampliar la protección a celular, correo, NIT, dirección y fecha de nacimiento el 11 de noviembre de 2026.

## Cambios

- `/lote/{id}/raw-vs-text` y su alias `/PlainText/{id}` devuelven cinco filas por defecto y aceptan como máximo cinco. Incluyen total de registros, página y número de páginas.
- La paginación cuenta líneas reales a través de bloques y archivos. Solo materializa la página solicitada y los metadatos necesarios; no ejecuta BETO ni modifica los registros.
- El filtro rechaza documentos ajenos al lote, en lugar de incorporar el archivo de otro lote.
- El backend protege los campos personales rotulados: nombres, apellidos, asesor, razón social, cédula, celular, teléfono, correo, NIT, domicilio y nacimiento. También protege las repeticiones de identificadores en códigos compuestos y metadatos de la fila.
- La protección sustituye el modo de demostración que solo ocultaba datos en el navegador. No existe un parámetro de la pantalla para desactivarla.
- Se excluyen muestras completas de hojas y metadatos sin uso. Las filas excepcionalmente largas tienen una vista abreviada indicada en pantalla y límites de longitud en la respuesta.
- La página usa React Query, un hook propio de consulta remota, el componente común de paginación y el límite común de cinco filas. Cambiar de archivo reinicia la página y las respuestas anteriores no se mezclan con la nueva selección.
- Botones compartidos, indicación de carga, reintento y avisos Sileo para los resultados de una actualización y los errores de consulta. Estas lecturas no crean notificaciones persistentes de tareas ni nuevos procesos.
- Los lotes cerrados permiten consultar y filtrar el texto. El aviso de solo lectura se mantiene y no se ofrece iniciar otro procesamiento desde esta pantalla.
- Se eliminan las etiquetas técnicas, el porcentaje de lectura inventado y los sustitutos `POS-034`, `MOD_CAT`, cantidades de subtotales y encabezados fijos. Los detalles estructurales reales quedan plegados.
- Los signos de interrogación de encabezados de encuestas dejan de contarse como valores dudosos. Las observaciones se comprueban sobre los valores de las filas.
- Se conservan los colores, temas y tipografías existentes. Las pestañas de archivo usan los componentes y colores compartidos.

## Verificación

- Línea base completa: 533 pruebas aprobadas, 11 omitidas y 7 fallos esperados anteriores.
- Suite completa final: 548 pruebas aprobadas, 11 omitidas y los mismos 7 fallos esperados. Sin regresiones en las pruebas ejecutadas.
- Pruebas aisladas de páginas que cruzan bloques y documentos, filtros, alias, validaciones HTTP, datos personales en todos los campos publicados, identificadores compuestos, encuestas, filas extensas y ausencia de escritura o inferencia.
- Compilación de producción del frontend correcta.
- Medición con datos reales, sin cargar archivos ni modificar el lote: 46.609 registros → 5 filas y 27.693 bytes de JSON; 15.196 registros → 5 filas y 20.549 bytes. Las medidas se tomaron antes del ajuste de las observaciones de encuestas.
- El recorrido recuenta las líneas al consultar una página; en las mediciones tomó aproximadamente 1,1 s para el lote mayor. No se mantiene una copia de todas las filas en memoria ni se repite el diagnóstico en cada fila.
- La verificación visual usa la cuenta Administrador. Las pruebas de API usan una sesión aislada.
- Navegador: páginas 1–5 y 6–10, filtro por archivo, textos desplegables, identificadores compuestos enmascarados, aviso Sileo de actualización, lotes cerrados y modo claro/oscuro.
- En el lote mayor las observaciones de formato pasan de 19.191 a 140 al excluir las preguntas de las encuestas; no se alteran los datos originales.

## Observaciones pendientes

- Se observaron edades fuera de rango en los datos originales. Su corrección corresponde a la revisión de integridad del loop 6, sin alterar datos operativos en este loop.
- El enmascarado ampliado de este loop se aplica a la consulta del paso ② y su alias. Los pasos ③ y ④ y sus exportaciones se revisarán en sus loops correspondientes.
- Los endpoints antiguos que no utiliza esta pantalla no cambian de contrato en este loop.
