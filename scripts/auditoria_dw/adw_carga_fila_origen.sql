-- ADW L0 · bloque idempotencia (C3): claves registradas frente a hechos cargados, por tabla
WITH claves AS (SELECT tabla, count(*) AS claves FROM public.carga_fila_origen GROUP BY tabla),
hechos AS (
  SELECT 'fact_rendimiento_academico' AS tabla, count(*) AS hechos FROM public.fact_rendimiento_academico
  UNION ALL SELECT 'fact_situacion_financiera', count(*) FROM public.fact_situacion_financiera
  UNION ALL SELECT 'fact_evaluacion_docente', count(*) FROM public.fact_evaluacion_docente
  UNION ALL SELECT 'fact_marketing', count(*) FROM public.fact_marketing
  UNION ALL SELECT 'fact_rentabilidad', count(*) FROM public.fact_rentabilidad)
SELECT coalesce(c.tabla, h.tabla) AS tabla, c.claves, h.hechos,
       round(c.claves::numeric / nullif(h.hechos, 0), 2) AS razon
FROM claves c FULL JOIN hechos h ON h.tabla = c.tabla
ORDER BY 1;
