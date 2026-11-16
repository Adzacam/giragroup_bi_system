-- F3S S-4 (D-A8b): comprobación de solo lectura sobre la copia del snapshot snapshot_dw_20261110_1201
-- Base: giragroup_db en beto_pg_s1 (tmpfs). Ejecutar con: psql ... -v ON_ERROR_STOP=1 -f f3s_d_a8b.sql
BEGIN READ ONLY;
SET TRANSACTION READ ONLY;

-- Q1. Metas registradas en 2024 por mes y categoría (fact_rentabilidad, monto_meta no nulo)
SELECT 'Q1_metas_2024' AS consulta, t.periodo_mes, c.nombre_categoria,
       SUM(r.monto_ejecutado) AS ejecutado_bs, SUM(r.monto_meta) AS meta_bs,
       COUNT(r.monto_meta)   AS filas_con_meta
FROM fact_rentabilidad r
JOIN dim_tiempo t ON r.id_tiempo = t.id_tiempo
JOIN dim_categoria_financiera c ON c.id_categoria = r.id_categoria
WHERE t.gestion = 2024
GROUP BY t.periodo_mes, c.nombre_categoria
ORDER BY t.periodo_mes, c.nombre_categoria;

-- Q1b. Conteo: meses de 2024 con meta registrada y meta de TECHOS_CERRADOS en 2024-12
SELECT 'Q1b_resumen_metas_2024' AS consulta,
       COUNT(DISTINCT t.periodo_mes) FILTER (WHERE r.monto_meta IS NOT NULL) AS meses_con_meta,
       COUNT(*) FILTER (WHERE r.monto_meta IS NOT NULL AND t.periodo_mes <> '2024-12') AS metas_fuera_de_diciembre,
       SUM(r.monto_meta) FILTER (WHERE r.monto_meta IS NOT NULL AND t.periodo_mes = '2024-12'
                                   AND c.nombre_categoria = 'TECHOS_CERRADOS') AS meta_techos_cerrados_2024_12
FROM fact_rentabilidad r
JOIN dim_tiempo t ON r.id_tiempo = t.id_tiempo
JOIN dim_categoria_financiera c ON c.id_categoria = r.id_categoria
WHERE t.gestion = 2024;

-- Q2. KPI-02 2024 con la misma lógica de kpi_service.py (último mes de la gestión: ejecutado del mes / meta del mes)
SELECT 'Q2_kpi02_2024' AS consulta, t.periodo_mes,
       SUM(r.monto_ejecutado) AS ejecutado_bs, SUM(r.monto_meta) AS meta_bs,
       ROUND((SUM(r.monto_ejecutado) / NULLIF(SUM(r.monto_meta),0)) * 100.0, 2) AS kpi02_pct,
       (SUM(r.monto_ejecutado) / NULLIF(SUM(r.monto_meta),0)) * 100.0 AS kpi02_pct_sin_redondear
FROM fact_rentabilidad r
JOIN dim_tiempo t ON r.id_tiempo = t.id_tiempo
WHERE t.gestion = 2024
GROUP BY t.periodo_mes
ORDER BY t.periodo_mes DESC
LIMIT 1;

-- Q3. KPI-03 2024 (ejecutado de la gestión / meta de la gestión)
SELECT 'Q3_kpi03_2024' AS consulta,
       SUM(r.monto_ejecutado) AS total_ejecutado_bs, SUM(r.monto_meta) AS total_meta_bs,
       ROUND((SUM(r.monto_ejecutado) / NULLIF(SUM(r.monto_meta),0)) * 100.0, 2) AS kpi03_pct,
       (SUM(r.monto_ejecutado) / NULLIF(SUM(r.monto_meta),0)) * 100.0 AS kpi03_pct_sin_redondear
FROM fact_rentabilidad r
JOIN dim_tiempo t ON r.id_tiempo = t.id_tiempo
WHERE t.gestion = 2024;

ROLLBACK;
