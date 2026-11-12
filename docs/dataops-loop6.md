# DataOps — loop 6: integridad hasta el CMI

Auditoría del 12 de noviembre de 2026. El usuario confirmó conservar los registros históricos y calcular el KPI 06 solo con captación comprobable. Para edades, módulos y fechas pidió una propuesta concreta antes de aplicar correcciones.

## Cambios aplicados

- El cargador de admisiones suma inscripciones sin inventar interesados. Marketing conserva un cero explícito de inscritos y no aumenta los interesados para forzar una conversión máxima del 100 %.
- Dos campos opcionales de marketing guardan la pareja de interesados e inscritos informada por la misma fuente. Solo las parejas explícitas, enteras, no negativas, con interesados positivos e inscritos no superiores a interesados alimentan el porcentaje. Los contadores generales de inscripciones se mantienen para las consultas de matrícula y proyección.
- Los registros históricos no se acreditan retrospectivamente como captación. La migración 014 añade los campos vacíos, cambia el cálculo SQL compartido por web y Power BI y mantiene la configuración de metas. `KPIService` usa el mismo criterio.
- Los dos flujos de procesamiento extraen los contadores por encabezados. La consolidación de DataOps ahora genera la misma clave de archivo, hoja, posición y contenido usada por el pipeline; las cargas de marketing y admisiones reutilizan el registro de filas para no sumar otra vez la misma fila. Esto no reconstruye ni resta duplicaciones históricas.
- Se impide crear módulos llamados únicamente «.», «......» o puntuación, tanto desde catálogo como desde el cargador. Los módulos históricos se conservan.
- Revisión ofrece «Comprobar conteos del lote», plegado inicialmente. Consulta de solo lectura, cinco documentos por página, disponible para Administrador y Auditor de Calidad; no ejecuta el modelo, no guarda ni inicia tareas.
- El panel distingue conteo registrado en la ingesta, líneas de texto, filas de lectura y aceptación directa guardadas, casos pendientes/resueltos y hechos de cada área. Las copias de staging para revisión no duplican el origen ni las pestañas. Una ausencia de lectura se presenta como «Sin dato», no como cero.
- Una fila de acta puede producir hechos por módulo; una encuesta, respuestas por pregunta. Un caso resuelto no prueba una fila aprobada ni su carga. Las inscripciones agregadas sin vínculo documental no se atribuyen a un archivo.
- El CMI explica los datos ausentes sin rellenarlos con cifras de otra gestión. La explicación sustituye a la descripción cuando falta el dato, evitando repetir texto. Se conserva tipografía, colores y ambos temas.

## Evidencia de los datos actuales

| Gestión académica | Hechos | Estudiantes distintos | Con nota | En revisión |
|---|---:|---:|---:|---:|
| 2024 | 12.120 | 3.147 | 11.869 | 459 |
| 2025 | 10.437 | 3.455 | 9.931 | 39 |
| Sin gestión | 61 | 60 | 0 | 61 |

No hay hechos académicos de 2026. Por eso KPI 07, 08, 10, 11, 16 y 21 carecen de base en ese año. Tampoco hay convenios con gestión 2026 para KPI 22. Las evaluaciones docentes y finanzas son fuentes distintas y sí pueden tener datos de 2026. El 100 % previo de KPI 06 procedía de igualar interesados e inscritos; ahora el cálculo devuelve ausencia de dato para esas cifras no acreditadas.

| Lote / documento | Filas registradas en ingesta | Líneas de texto | Lectura guardada | Directas en lectura | Casos pendientes / resueltos | Hechos vinculados |
|---|---:|---:|---:|---:|---|---|
| 1 / 1 | 19.121 | 19.119 | Sin dato | Sin dato | 0 / 0 | Sin hechos vinculados |
| 1 / 2 | 11.454 | 11.456 | Sin dato | Sin dato | 0 / 2 | Sin hechos vinculados |
| 1 / 3 | 16.034 | 16.034 | Sin dato | Sin dato | 0 / 2 | 1 financiero |
| 2 / 19 | 15.196 | 15.196 | 15.196 | 15.196 | 0 / 13 | Sin hechos con vínculo documental |

La tabla informa evidencia almacenada, no certifica la corrección del historial. No se reanalizaron lotes cerrados para fabricar lecturas ausentes. Las diferencias entre conteos de ingesta y texto del lote 1 quedan visibles; los totales del lote coinciden por compensación y no justifican ocultar la diferencia por archivo.

Antes y después de la migración: **15.257 agregados, 45.568 interesados históricos y 45.568 inscripciones**, sin cambiar esos contadores. Los nuevos campos de captación están vacíos en todos los agregados históricos. Se verificó el KPI 06 nulo en la vista semántica por gestión.

El registro de cargas identifica 15.196 filas del documento 12. Los documentos 12 y 19 comparten huella de archivo. La tabla de marketing carece de un vínculo documental por agregado: no permite reconstruir una conciliación histórica completa ni deduplicar por suposición. La nueva protección de reintentos no sustituye esa reconstrucción.

## Correcciones históricas propuestas, sin aplicar

- La fuente de admisiones tiene 193 filas con «EDAD L» igual a 127 y nacimiento no interpretable. Son filas, no un conteo de personas únicas. Ninguna de las 14.079 personas activas tiene edad guardada; no se introducen edades nuevas.
- Quedan dos módulos solo con puntos y cinco nombres numéricos. Los módulos 4937 y 4957 tienen tres agregados de marketing que suman seis inscripciones. No se fusionan ni eliminan.
- No existe actualmente ningún programa guardado como «Programa General»; 779 módulos carecen de programa. Los sustitutos de visualización del código no prueban que se haya guardado ese valor en la base.
- Hay fechas del calendario en 2005, 2020, 2021, 2028 y 2034 que no implican por sí solas un hecho incorrecto. El convenio 25 sí vincula el inicio 2034-01-12 con gestión 2024 y fin 2024-03-02; ya estaba marcado para revisión. Las diferencias entre año de inicio y gestión de otros convenios no se corrigen automáticamente.

La [propuesta detallada](propuesta-integridad-loop6.md) contiene cambios antes/después, alcance, comprobaciones y reversión. El [manifiesto](propuesta-integridad-loop6.json) identifica las 193 filas sin datos personales, los dos módulos y el convenio. El generador usa una transacción PostgreSQL de solo lectura. La propuesta conserva los originales y requiere aprobación por apartados.

## Verificación

- Pruebas nuevas: captación explícita y ausente, cero real, mezcla con admisiones, reintentos, valores inválidos, fechas fuera del rango existente, módulos de puntuación, unidades de conteo, ausencia de lectura, consulta sin escrituras, cinco documentos y permisos por rol.
- Integración con archivo `.xlsx` temporal y SQLite aislado: dos filas de acta → dos filas de lectura aceptadas → cuatro hechos académicos por módulo → promedio 75 y aprobación 75 %. La gestión siguiente permanece sin dato. Se sustituye exclusivamente la respuesta del servicio externo de BETO y se desactiva el diagnóstico opcional que consulta catálogos externos; se ejercitan ingesta, serialización, reglas, extracción, consolidación, dimensiones, hechos y cálculo reales. No es una medición de precisión del modelo.
- Compilación de producción del frontend correcta. Migración aplicada en PostgreSQL local; comprobación de contadores y de las vistas semánticas de solo lectura. No había tareas activas en los reinicios.
- Navegador con cuenta Administrador: conteos de lotes 1 y 2 cerrados, ausencia de lectura histórica, origen frente a texto, consulta en claro y oscuro; CMI de 2025 con matrícula 3.455, promedio 79 y aprobación 85,6 %, CMI de 2026 sin valores académicos de relleno, historial con cuatro filas y cierre, KPI 06 sin 100 % artificial. Se restauró el modo claro.
- No se subieron archivos, resolvieron casos, consolidaron lotes ni modificaron edades, nombres de módulos o fechas históricas en la aplicación real. Las escrituras de prueba se realizaron en bases aisladas.
- Suite final: **628 aprobadas, 11 omitidas y los mismos 7 fallos esperados**, con 45 advertencias. Línea base del loop 5: 604 aprobadas. Las 24 pruebas nuevas están incluidas en la suite. Las omitidas dependen de la configuración de readiness y los fallos esperados corresponden a hallazgos previos.
- Consulta de integridad en solo lectura: lote 1, tres documentos, 1.202 bytes en aproximadamente 0,269 s; lote 2, un documento, 666 bytes en aproximadamente 0,380 s. Son mediciones locales puntuales, no una prueba de carga.
