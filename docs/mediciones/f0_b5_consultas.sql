-- B-5: ejecutar EXCLUSIVAMENTE en beto_pg_tmpfs/giragroup_db (copia histórica).
-- Fuentes: time_series_extractor.QUERIES[META_ANUAL], forecast_service._SQL_META_VS_EJECUTADO,
-- bi.vw_cmi_valores (migraciones 006/014). No usa la carga mensual F0.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL TIME ZONE 'America/La_Paz';
SELECT current_database() AS base, current_date AS fecha_servidor,
       current_setting('transaction_read_only') AS solo_lectura;
-- Serie exactamente usada por OLS anual: PROGRAMAS, ejecutado no nulo, gestiones cerradas.
WITH anual AS (
 SELECT dt.gestion AS anio, SUM(fr.monto_ejecutado)::numeric AS observado_bs,
        COUNT(DISTINCT dt.mes) AS meses, COUNT(*) AS filas
 FROM public.fact_rentabilidad fr
 JOIN public.dim_categoria_financiera dcf ON fr.id_categoria=dcf.id_categoria
 JOIN public.dim_tiempo dt ON fr.id_tiempo=dt.id_tiempo
 WHERE dcf.nombre_categoria='PROGRAMAS' AND fr.monto_ejecutado IS NOT NULL
   AND dt.gestion < EXTRACT(YEAR FROM CURRENT_DATE)
 GROUP BY dt.gestion
), ajuste AS (
 SELECT COUNT(*) AS n, regr_slope(observado_bs::float, anio::float) AS pendiente,
        regr_intercept(observado_bs::float, anio::float) AS intercepto FROM anual
)
SELECT a.*, j.n, j.pendiente, j.intercepto,
 CASE WHEN j.n>=3 THEN j.pendiente*a.anio+j.intercepto END AS ajustado_ols_bs,
 CASE WHEN j.n>=3 THEN j.pendiente*a.anio+j.intercepto-a.observado_bs END AS delta_ajustado_observado_bs,
 CASE WHEN j.n>=3 THEN 100.0*(j.pendiente*a.anio+j.intercepto-a.observado_bs)/NULLIF(a.observado_bs,0) END AS delta_pct
FROM anual a CROSS JOIN ajuste j ORDER BY a.anio;
-- 2025 por categoría: delimita PROGRAMAS, otros ingresos y egresos sin confundir universos.
SELECT dt.gestion, dc.tipo, dc.nombre_categoria, COUNT(*) AS filas,
       COUNT(DISTINCT dt.mes) AS meses, SUM(fr.monto_ejecutado) AS ejecutado_bs,
       SUM(fr.monto_meta) AS meta_bs
FROM public.fact_rentabilidad fr
JOIN public.dim_tiempo dt ON dt.id_tiempo=fr.id_tiempo
JOIN public.dim_categoria_financiera dc ON dc.id_categoria=fr.id_categoria
WHERE dt.gestion=2025 GROUP BY dt.gestion,dc.tipo,dc.nombre_categoria
ORDER BY dc.tipo,dc.nombre_categoria;
-- Dos universos mensuales. KPI-03: todos INGRESO; macro/OLS: PROGRAMAS.
WITH base AS (
 SELECT dt.gestion,dt.mes,dc.tipo,dc.nombre_categoria,fr.monto_ejecutado,fr.monto_meta
 FROM public.fact_rentabilidad fr JOIN public.dim_tiempo dt ON dt.id_tiempo=fr.id_tiempo
 JOIN public.dim_categoria_financiera dc ON dc.id_categoria=fr.id_categoria WHERE dt.gestion=2025
), mes AS (
 SELECT 'KPI03_INGRESO' AS universo,gestion,mes,COALESCE(SUM(monto_ejecutado),0) AS ejecutado,
        COALESCE(SUM(monto_meta),0) AS meta FROM base WHERE tipo='INGRESO' GROUP BY gestion,mes
 UNION ALL
 SELECT 'MACRO_PROGRAMAS',gestion,mes,SUM(monto_ejecutado),SUM(monto_meta)
 FROM base WHERE nombre_categoria='PROGRAMAS' GROUP BY gestion,mes
)
SELECT universo,gestion,COUNT(*) AS meses_con_fila,COUNT(*) FILTER(WHERE ejecutado>0) AS meses_ejecutados,
       SUM(ejecutado) AS ejecutado_bs,SUM(meta) AS meta_anual_bs,
       SUM(meta) FILTER(WHERE ejecutado>0) AS meta_a_la_fecha_bs,
       100.0*SUM(ejecutado)/NULLIF(SUM(meta) FILTER(WHERE ejecutado>0),0) AS cumplimiento_a_la_fecha_pct,
       100.0*SUM(ejecutado)/NULLIF(SUM(meta),0) AS cumplimiento_anual_pct,
       array_agg(mes ORDER BY mes) AS meses,
       json_agg(json_build_object('mes',mes,'ejecutado_bs',ejecutado,'meta_bs',meta) ORDER BY mes) AS serie_mensual
FROM mes GROUP BY universo,gestion ORDER BY universo;
SELECT gestion,codigo,valor FROM bi.vw_cmi_valores WHERE gestion=2025 AND codigo='KPI-03';
ROLLBACK;
