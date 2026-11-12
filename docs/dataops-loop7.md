# DataOps — loop 7: división del router y verificación final

Se divide `backend/routers/dataops.py` (4.630 líneas) en un paquete por pasos, sin cambiar rutas, métodos, contratos ni la protección por rol.

## Estructura

`backend/routers/dataops/` conserva la importación `from routers import dataops` y el objeto `router` (prefijo `/api/v1/dataops`, acceso solo para Administrador y Auditor de Calidad).

| Módulo | Contenido |
|---|---|
| `__init__.py` | Une los módulos bajo un solo router y expone los nombres que usan otros módulos y las pruebas. |
| `_comun.py` | Constantes de umbrales y modelos de solicitud compartidos. |
| `extraccion.py` | Extracción de entidades de una línea de texto (BETO por reglas y catálogo). |
| `evaluacion.py` | Resolución de documentos de un lote, evaluación, caché, huella y estado del flujo. |
| `ingesta.py` | Paso ①: carga, procesamiento por lote, historial, bitácora y matriz de normalización. |
| `lectura.py` | Pasos ② y ③: texto preparado, resultados de BETO, integridad, tareas y revelado auditado de la cédula. |
| `revision.py` | Paso ④: bandeja, grupos, resoluciones, bloqueos y avisos. |
| `consolidacion.py` | Consolidación de registros aprobados en el Data Warehouse. |
| `maestros.py` | Catálogos, vínculos de entidades, comparación difusa, inferencia y telemetría. |

Las dependencias van en un solo sentido (`_comun` → `extraccion` → `evaluacion` → pasos); no hay importaciones circulares.

## Verificación

- Las 45 rutas son idénticas antes y después (ruta, método y función) y cada ruta sigue resolviéndose con el mismo manejador.
- Ningún nombre global queda sin definir en los ocho módulos (revisión de cada referencia compilada).
- Las pruebas que parchean funciones usan `tests/dataops_parches.py`: aplica el parche en cada módulo donde el nombre existe, como cuando todo vivía en un archivo.
- Suite completa de Python y recorrido de la API real: lectura de 15 endpoints del lote cerrado, sin datos personales (cédula, correo, celular, NIT) en las respuestas.
- Compilación del frontend correcta; pasos ①–④ cargan con 5 filas por página y cédulas enmascaradas.

## Pendiente

- `extract_entities_from_line` (635 líneas) y `_evaluar_documentos_lote` (530) siguen siendo funciones largas; conviene partirlas en una segunda pasada con pruebas por tramo.
- Los scripts que generan tablas de la tesis citan `backend/routers/dataops.py` con cifras fijas (2.176 sentencias); se actualizan con el documento.
