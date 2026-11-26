# Pruebas E2E de GiraGroup BI V2

Ejecución parcial en `http://localhost:5173` con sesión de administrador.

## Entorno

Los nueve servicios de Compose estaban activos. La API respondió healthy con la base conectada. BETO respondió online desde su contenedor. La consulta de solo lectura confirmó 51 tablas, 10 vistas BI, 23 KPI, cero lotes en la DW activa y cero filas en las diez tablas de hechos. Los cinco Excel iniciales y los dos candidatos incrementales existen en `uploads/data/`.

La API activa usa el volumen persistente de `giragroup_db`. La instancia tmpfs existente es independiente. La ejecución se limitó a navegación, comprobaciones de interfaz y consultas de solo lectura. No se cargaron archivos ni se consolidaron lotes.

## Resultados

| Caso | Estado | Evidencia o condición pendiente |
|---|---|---|
| TC-01 | Parcial | La raíz redirigió a /v2/login. Pendiente verificar red y consola de esa navegación. |
| TC-02 | PASS | La sesión iniciada por el usuario abrió /v2/dashboard con rol Administrador. |
| TC-03 | PASS | /dashboard?ui=v1 mostró el CMI y conservó la ruta V1. |
| TC-04 | Parcial | La campana desplegó tres avisos, coherentes con el contador. Pendiente contraste en ambos temas. |
| TC-05 | FAIL | Escape cerró el panel. El clic sobre el encabezado externo dejó el panel abierto. El enlace final abrió /notificaciones con el shell V1. |
| TC-06 | Parcial | El centro mostró el listado, tres no leídas y controles de filtro y marcado. Pendiente probar paginación y marcado. |
| TC-07 | PASS | Stepper, dropzone y reglas visibles. Sin menciones de Tarea N en la franja inspeccionada. |
| TC-08 | Parcial | Procesar archivos (0) y Vaciar cola (0) deshabilitados. Pendiente contraste en ambos temas. |
| TC-09–TC-14 | Pendiente | Selección de Excel, vista previa, mapeo, procesamiento e historial requieren ejecutar el lote de prueba. |
| TC-15–TC-20 | Pendiente | El paso BETO requiere un lote procesado en el entorno aislado. |
| TC-21–TC-27 | Pendiente | La ruta de revisión general cargó y pidió seleccionar un lote. Revisar, resolver, reabrir y consolidar requieren el lote de prueba. |
| TC-28 | Parcial | Catálogo con paginación declarada de veinte y controles Solo genéricos, Sin programa y uso. Pendientes conteos y referencias posconsolidación. |
| TC-29–TC-31 | Pendiente | Modal de limpieza, composición del catálogo institucional y ajuste de tarjetas con nombres largos. |
| TC-32 | Parcial | CMI visible y 23 KPI confirmados en SQL. El tablero indicó que la DW carecía de datos consolidados. |
| TC-33 | Parcial | Abrió la pantalla de alertas tempranas. Pendientes la máscara, la revelación individual y su auditoría sobre datos de prueba. |
| TC-34–TC-35 | Pendiente | Indicadores docentes, catálogo curricular y serie de proyección. |
| TC-36 | Parcial | Abrió el panel de recaudación. Pendientes la cartera y la conciliación de cifras. |
| TC-37 | Pendiente | Metas y proyección financiera sobre el lote consolidado. |
| TC-38 | Parcial | El centro mostró selector, formatos, filtros y bitácora. Pendientes descargas Excel y PDF. |
| TC-39 | Parcial | Cargaron Auditoría, Usuarios, Catálogos y Ajustes. API conectada. Pendiente auditoría del nuevo lote. |
| TC-40–TC-42 | Pendiente | La carga incremental requiere el escenario A consolidado en tmpfs. |
| TC-43 | Parcial | 42 mediciones en siete rutas, tres tamaños y dos temas. Ningún desbordamiento del documento en esas mediciones. Pendientes contraste, fluidez y contenido con datos. |
| TC-44 | Parcial | Hallazgos reproducidos abajo. Pendiente completar la matriz con evidencia del lote y capturas archivadas. |

## Hallazgos

1. **Navegación funcional · TC-05.** En /v2/dashboard, abrir la campana y pulsar Ver todas las notificaciones. La URL observada es /notificaciones y aparece el shell V1. Se esperaba /v2/notificaciones.
2. **Mejora heurística · TC-05.** En /v2/dashboard, abrir la campana y pulsar el encabezado Cuadro de Mando Integral. El panel sigue abierto. Escape sí lo cierra.
3. **Estado previo sin reproducir.** La campana mostraba una alerta de preparación de revisión interrumpida para el lote #1, junto con avisos de lectura BETO y carga completadas. El historial de la vista de carga y la consulta de la DW activa mostraron cero lotes. Se desconoce el origen de esa diferencia.
