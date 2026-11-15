-- F2-2 (B-2 / P-2): Consulta de KPIs 12..15 y 17..20 en dw_f2 (2025 y total) + sensibilidad requiere_revision
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;

SELECT codigo, nombre, unidad, perspectiva
FROM bi.ref_kpi
WHERE codigo IN ('KPI-12','KPI-13','KPI-14','KPI-15','KPI-17','KPI-18','KPI-19','KPI-20')
ORDER BY codigo;

SELECT gestion, codigo, valor
FROM bi.vw_cmi_valores
WHERE codigo IN ('KPI-12','KPI-13','KPI-14','KPI-15','KPI-17','KPI-18','KPI-19','KPI-20')
  AND (gestion = 2025 OR gestion IS NULL)
ORDER BY codigo, gestion;

-- Desglose por requiere_revision en hechos relevantes
SELECT 'fact_rendimiento_academico' AS tabla,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE requiere_revision) AS en_revision,
       ROUND(AVG(nota_final)::numeric, 4) AS prom_con_rev,
       ROUND(AVG(nota_final) FILTER (WHERE NOT requiere_revision)::numeric, 4) AS prom_sin_rev,
       ROUND(100.0 * COUNT(*) FILTER (WHERE asistencia_pct >= 80) / NULLIF(COUNT(*), 0), 4) AS asist80_con_rev,
       ROUND(100.0 * COUNT(*) FILTER (WHERE asistencia_pct >= 80 AND NOT requiere_revision) / NULLIF(COUNT(*) FILTER (WHERE NOT requiere_revision), 0), 4) AS asist80_sin_rev
FROM public.fact_rendimiento_academico
UNION ALL
SELECT 'fact_evaluacion_docente',
       COUNT(*),
       COUNT(*) FILTER (WHERE requiere_revision),
       ROUND(AVG(puntuacion)::numeric, 4),
       ROUND(AVG(puntuacion) FILTER (WHERE NOT requiere_revision)::numeric, 4),
       NULL,
       NULL
FROM public.fact_evaluacion_docente
UNION ALL
SELECT 'fact_situacion_financiera',
       COUNT(*),
       COUNT(*) FILTER (WHERE requiere_revision),
       ROUND(SUM(monto_deuda)::numeric, 2),
       ROUND(SUM(monto_deuda) FILTER (WHERE NOT requiere_revision)::numeric, 2),
       NULL,
       NULL
FROM public.fact_situacion_financiera;

ROLLBACK;
