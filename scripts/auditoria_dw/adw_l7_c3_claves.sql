-- ADW L7-C3: claves de idempotencia frente a hechos, por tabla y documento (solo SELECT).
-- El cargador registra 2 claves por fila de origen (posición y contenido: _reclamar_fila_origen). Filas reclamadas = claves / 2.
WITH claves AS (SELECT tabla, id_documento, count(*) AS claves FROM public.carga_fila_origen GROUP BY 1, 2),
hechos AS (
  SELECT 'fact_rendimiento_academico' AS tabla, id_documento, count(*) AS hechos FROM public.fact_rendimiento_academico GROUP BY 2
  UNION ALL SELECT 'fact_situacion_financiera', id_documento, count(*) FROM public.fact_situacion_financiera GROUP BY 2
  UNION ALL SELECT 'fact_evaluacion_docente', id_documento, count(*) FROM public.fact_evaluacion_docente GROUP BY 2
  UNION ALL SELECT 'fact_rentabilidad', id_documento, count(*) FROM public.fact_rentabilidad GROUP BY 2
  UNION ALL SELECT 'fact_techo_convenio', id_documento, count(*) FROM public.fact_techo_convenio GROUP BY 2
  UNION ALL SELECT 'fact_planificacion_programa', id_documento, count(*) FROM public.fact_planificacion_programa GROUP BY 2)
SELECT c.tabla, c.id_documento, d.nombre_archivo, c.claves,
       round(c.claves / 2.0, 1) AS filas_reclamadas, h.hechos,
       round(c.claves::numeric / nullif(h.hechos, 0), 2) AS razon_claves_hechos,
       round(c.claves / 2.0 - coalesce(h.hechos, 0), 1) AS reclamadas_sin_hecho
FROM claves c
LEFT JOIN hechos h ON h.tabla = c.tabla AND h.id_documento = c.id_documento
LEFT JOIN public.dim_origen_documental d ON d.id_documento = c.id_documento
ORDER BY c.tabla, c.id_documento;
