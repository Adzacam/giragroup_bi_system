# Contexto de datos del CMI — A0

Mapa de definiciones y fórmulas leído del código local para revisión de Lean. La definición funcional se contrasta con la fórmula en A2. Las referencias describen el código disponible, cuya correspondencia con el despliegue queda por verificar en navegador y API.

## Scorecard

`GET /api/v1/cmi/scorecard` consume `bi.vw_cmi_scorecard` y `bi.vw_cmi_perspectiva`. `GET /api/v1/cmi/resumen` sirve las series por gestión. El historial de un KPI usa `GET /api/v1/cmi/kpis/{codigo}/historial`. El desglose de cada perspectiva usa `GET /api/v1/cmi/perspectivas/{codigo}/detalle`.

`bi.vw_cmi_scorecard` cruza las gestiones disponibles con los KPI activos de las perspectivas activas, enlaza los valores, redondea a dos decimales y calcula la diferencia con la gestión anterior en la vista. `bi.ref_kpi` aporta la etiqueta, unidad, sentido y configuración del semáforo. Los índices ponderados incluyen los puntajes disponibles. El índice global de la API se construye a partir de las perspectivas visibles por rol.

Las fórmulas de valor están en `backend/scripts/migrations/019_vista_planificacion_kpi23.sql:126`. Las vistas de agregación, el riesgo y las referencias originales están en `006_capa_semantica_cmi.sql`. La migración 013 renombra KPI-10, 014 redefine la conversión y 019 incorpora KPI-23. Cuando se indica gestión, los hechos con `id_tiempo` la obtienen desde `public.dim_tiempo`.

| KPI | Perspectiva | Unidad | Qué calcula el código | Fuente principal |
|---|---|---|---|---|
| KPI-01 | Financiera | Bs | Total pagado de la gestión dividido entre matrícula efectiva, con respaldo en el conteo distinto de estudiantes de cartera cuando la matrícula falta o es cero. | `fact_situacion_financiera.monto_pagado, id_estudiante` y `fact_rendimiento_academico.id_estudiante` |
| KPI-02 | Financiera | % | Ejecutado sobre meta del último mes de la gestión con ingreso ejecutado mayor que cero. | `fact_rentabilidad.monto_ejecutado, monto_meta, id_categoria` y `dim_categoria_financiera.tipo` |
| KPI-03 | Financiera | % | Ejecutado de la gestión sobre la suma de metas de los meses con ejecución positiva. | `fact_rentabilidad` de tipo `INGRESO` |
| KPI-04 | Financiera | Estudiantes | Estudiantes distintos con al menos una fila con dos o más cuotas impagas o estado previsionable. | `fact_situacion_financiera.id_estudiante, cuotas_impagas, estado_cartera` |
| KPI-05 | Financiera | % | Suma de conteos distintos de estudiantes en mora y previsionables sobre la suma de los conteos en esos dos estados y vigente. El conteo distinto se hace por estado. | `fact_situacion_financiera.id_estudiante, estado_cartera` |
| KPI-06 | Clientes | % | Suma de inscritos de captación sobre suma de leads de captación. Solo entran filas con leads positivos e inscritos entre cero y el número de leads. | `fact_marketing.inscritos_captacion, leads_captacion` |
| KPI-07 | Aprendizaje | Puntos | Promedio de las notas finales registradas. | `fact_rendimiento_academico.nota_final` |
| KPI-08 | Aprendizaje | % | Notas finales de 70 o más sobre el total de notas finales informadas. | `fact_rendimiento_academico.nota_final` |
| KPI-09 | Aprendizaje | Estudiantes | Estudiantes en la matriz de riesgo cuyo promedio de notas es de 70 o menos. | `bi.vw_riesgo_estudiante.regla_a_academico` y `fact_rendimiento_academico.nota_final` |
| KPI-10 | Procesos internos | % | Confianza media de extracción multiplicada por 100. El promedio incluye reglas de encabezado y BETO según la descripción vigente. | `fact_rendimiento_academico.nivel_confianza_ia` |
| KPI-11 | Procesos internos | % | Filas con confianza de 0,85 o más sobre las filas con confianza informada. | `fact_rendimiento_academico.nivel_confianza_ia` |
| KPI-12 | Financiera | % | Variación entre ingresos ejecutados de la gestión y los de los mismos meses de la gestión anterior. Selecciona meses con ingreso actual mayor que cero y correspondencia en ambas gestiones. | `fact_rentabilidad.monto_ejecutado` de tipo `INGRESO` |
| KPI-13 | Financiera | % | Ejecutado de la gestión sobre suma de metas de la gestión. | `fact_rentabilidad.monto_ejecutado, monto_meta` de tipo `INGRESO` |
| KPI-14 | Financiera | Bs | Diferencia entre suma de metas y suma de ingresos ejecutados de la gestión, con piso cero y meta positiva. | `fact_rentabilidad.monto_ejecutado, monto_meta` de tipo `INGRESO` |
| KPI-15 | Financiera | % | Deuda de estados Mora, En Mora y Previsionable sobre deuda total. | `fact_situacion_financiera.monto_deuda, estado_cartera` |
| KPI-16 | Clientes | % | Estudiantes distintos con incumplimiento efectivo mayor a 30 % sobre estudiantes distintos en hechos de rendimiento. Usa el mayor entre incumplimiento reportado e inasistencia y aplica los valores por defecto de la vista si faltan esos campos. | `fact_rendimiento_academico.id_estudiante, incumplimiento_actividades_pct, asistencia_pct` |
| KPI-17 | Aprendizaje | Estudiantes | Estudiantes de la matriz con al menos dos de las reglas académica, deserción y financiera activas. | `bi.vw_riesgo_estudiante.k_reglas`, hechos de rendimiento y situación financiera |
| KPI-18 | Procesos internos | Registros | Filas pendientes de resolución agrupadas por el año de creación del registro. | `stg_entidad_no_resuelta.resuelto, created_at` |
| KPI-19 | Aprendizaje | % | Promedio del puntaje normalizado por la escala máxima de cada respuesta de tipo DOCENTE. | `fact_evaluacion_docente.puntuacion, escala_max, tipo_pregunta` |
| KPI-20 | Clientes | % | Promedio del puntaje normalizado por la escala máxima de cada respuesta de tipo INSTITUCIONAL. | `fact_evaluacion_docente.puntuacion, escala_max, tipo_pregunta` |
| KPI-21 | Clientes | Estudiantes | Estudiantes distintos en hechos de rendimiento de la gestión. | `fact_rendimiento_academico.id_estudiante` |
| KPI-22 | Clientes | Inscritos | Suma de inscritos por convenio para la gestión presente en el hecho. | `fact_techo_convenio.gestion, n_inscritos` |
| KPI-23 | Procesos internos | % | Programas iniciados sobre planificados, deduplicados por período de planificación y POS normalizado, con clave de origen para POS ausente. | `fact_planificacion_programa.id_tiempo_plan, pos_code_fuente, clave_fila_origen, estado_fuente` |

Puntos de contraste para A2. KPI-06 usa `leads_captacion`, por lo que S2 requiere perfilar ese campo. KPI-11 usa la banda de confianza como proxy de automatización y la fórmula prescinde de `requiere_revision`. KPI-21 cuenta el hecho de rendimiento sin un filtro explícito de nota informada. DA2 se conserva como decisión funcional. El código de KPI-14 agrega la gestión completa y A2 debe documentar cómo se relaciona ese acumulado con el último mes con ejecución positiva.

## Analítica predictiva

El endpoint `GET /api/v1/forecast/analitica-macro` sirve los cuatro casos. El detalle de campos ya se encuentra en [contexto_datos_prediccion.md](contexto_datos_prediccion.md). La implementación se distribuye entre `backend/services/forecast_service.py` y `pipeline/analytics/time_series_extractor.py`.

| Caso | Qué se interpreta | Fuente y cálculo |
|---|---|---|
| 1. Demanda global | Serie histórica mensual de inscritos, proyección e incertidumbre. | Suma de `fact_marketing.inscritos` por período de `dim_tiempo`. Holt-Winters amortiguado, estacionalidad de 12 meses y tendencia descriptiva OLS mensual. |
| 2. Viabilidad por programa | Historial por programa, sugerencia por fila y proyecciones por segmento. | `fact_marketing.inscritos`, `dim_modulo.programa` y `dim_tiempo.gestion`. Los segmentos consultan `fact_forecast` como caché y, en ausencia de una entrada aplicable, calculan sobre la serie mensual. |
| 3. Metas mensuales | Meta, ejecutado, cierre mensual estimado y avance proyectado. | `fact_rentabilidad.monto_meta, monto_ejecutado`, categoría `PROGRAMAS`. La gráfica histórica agrupa por mes. La serie de Holt-Winters toma el ejecutado y usa la meta cuando el ejecutado es nulo. |
| 4. Metas anuales | Recaudación y meta de la gestión actual, con tendencia anual descriptiva. | `fact_rentabilidad.monto_ejecutado, monto_meta`, categoría `PROGRAMAS`. La tarjeta agrega la gestión calendario actual. El historial anual de la regresión agrega las gestiones cerradas. |

La configuración de referencia establece hold-out de seis meses para la evaluación de Holt-Winters, OLS mensual sobre la serie de referencia de 40 meses y OLS anual de uso descriptivo. `n_observaciones` en la respuesta indica la longitud efectiva del caso 1. La ruta macro puede activar persistencia en `fact_forecast` cuando el caso 2 vuelve a calcular un segmento. Una sesión destinada a verificar estos gráficos requiere una copia de trabajo o un entorno que permita impedir escrituras en la DW viva.
