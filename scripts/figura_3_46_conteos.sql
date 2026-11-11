-- Figura 3.46: constelación del DW (9 hechos + 7 dimensiones + 1 bridge) con conteo de filas reales
SELECT tipo, tabla, replace(to_char(filas,'FM999,999,999'), ',', '.') AS filas FROM (
  SELECT 1 o,'HECHO' tipo,'fact_cobranzas_proyectadas' tabla,(SELECT count(*) FROM fact_cobranzas_proyectadas) filas UNION ALL
  SELECT 1,'HECHO','fact_costo_programa',(SELECT count(*) FROM fact_costo_programa) UNION ALL
  SELECT 1,'HECHO','fact_evaluacion_docente',(SELECT count(*) FROM fact_evaluacion_docente) UNION ALL
  SELECT 1,'HECHO','fact_forecast',(SELECT count(*) FROM fact_forecast) UNION ALL
  SELECT 1,'HECHO','fact_marketing',(SELECT count(*) FROM fact_marketing) UNION ALL
  SELECT 1,'HECHO','fact_rendimiento_academico',(SELECT count(*) FROM fact_rendimiento_academico) UNION ALL
  SELECT 1,'HECHO','fact_rentabilidad',(SELECT count(*) FROM fact_rentabilidad) UNION ALL
  SELECT 1,'HECHO','fact_situacion_financiera',(SELECT count(*) FROM fact_situacion_financiera) UNION ALL
  SELECT 1,'HECHO','fact_techo_convenio',(SELECT count(*) FROM fact_techo_convenio) UNION ALL
  SELECT 2,'DIMENSION','dim_categoria_financiera',(SELECT count(*) FROM dim_categoria_financiera) UNION ALL
  SELECT 2,'DIMENSION','dim_docente',(SELECT count(*) FROM dim_docente) UNION ALL
  SELECT 2,'DIMENSION','dim_estudiante',(SELECT count(*) FROM dim_estudiante) UNION ALL
  SELECT 2,'DIMENSION','dim_meta',(SELECT count(*) FROM dim_meta) UNION ALL
  SELECT 2,'DIMENSION','dim_modulo',(SELECT count(*) FROM dim_modulo) UNION ALL
  SELECT 2,'DIMENSION','dim_origen_documental',(SELECT count(*) FROM dim_origen_documental) UNION ALL
  SELECT 2,'DIMENSION','dim_tiempo',(SELECT count(*) FROM dim_tiempo) UNION ALL
  SELECT 3,'BRIDGE','bridge_modulo_docente',(SELECT count(*) FROM bridge_modulo_docente)
) t ORDER BY o, tabla;
