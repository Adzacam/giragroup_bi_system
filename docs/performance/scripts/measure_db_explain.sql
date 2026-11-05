-- =============================================================================
-- Script de Diagnóstico y Medición SQL (EXPLAIN ANALYZE, BUFFERS + Catálogo)
-- Sistema BI GiraGroup - Auditoría de Rendimiento (PostgreSQL DW :5434)
--
-- Verificado contra DDL real en db/schema.sql:
--   - fact_rendimiento_academico (id_hecho_aca, id_estudiante, id_docente, id_modulo,
--     id_tiempo, id_documento, nota_final, asistencia_pct, incumplimiento_actividades_pct,
--     nivel_confianza_ia, requiere_revision, estado_academico, tipo_alerta)
--   - fact_situacion_financiera (id_hecho_fin, id_estudiante, id_modulo, id_categoria_fin,
--     id_tiempo, id_documento, monto_deuda, monto_pagado, cuotas_impagas, estado_cartera)
--   - fact_rentabilidad (id_hecho_rent, id_modulo, id_tiempo, id_categoria, monto_ejecutado, monto_meta)
--   - fact_marketing (id_hecho_mkt, id_modulo, id_tiempo, leads, reservas, inscritos, costo_programa)
--   - dim_estudiante (id_estudiante, nombre_completo, codigo_estudiante, ci, ci_numero, programa_origen, deprecado)
--   - dim_modulo (id_modulo, nombre_modulo, programa, pos_code)
--   - dim_tiempo (id_tiempo, fecha, gestion, semestre, trimestre, mes, periodo_mes)
--
-- Ejecución (modo solo lectura, no modifica tablas ni índices):
--   psql -h 127.0.0.1 -p 5434 -U giragroup_user -d giragroup_db \
--        -f docs/performance/scripts/measure_db_explain.sql
-- =============================================================================

\timing on
\pset pager off

\echo '========================================================================='
\echo '1. VOLUMEN DE TABLAS, TAMAÑO EN DISCO Y DEAD TUPLES (VACUUM STATUS)'
\echo '========================================================================='
SELECT
    schemaname,
    relname AS tabla,
    n_live_tup AS filas_vivas,
    n_dead_tup AS filas_muertas,
    pg_size_pretty(pg_total_relation_size(relid)) AS tamano_total,
    pg_size_pretty(pg_indexes_size(relid)) AS tamano_indices,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

\echo ''
\echo '========================================================================='
\echo '2. AUDITORÍA DE SEQUENTIAL SCANS VS INDEX SCANS'
\echo '========================================================================='
SELECT
    relname AS tabla,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    CASE
        WHEN (seq_scan + COALESCE(idx_scan, 0)) > 0
        THEN ROUND(100.0 * seq_scan / (seq_scan + COALESCE(idx_scan, 0)), 2)
        ELSE 0
    END AS pct_seq_scan
FROM pg_stat_user_tables
ORDER BY seq_tup_read DESC;

\echo ''
\echo '========================================================================='
\echo '3. DETECCIÓN DE ÍNDICES REDUNDANTES / NO UTILIZADOS'
\echo '========================================================================='
SELECT
    s.relname AS tabla,
    s.indexrelname AS indice,
    s.idx_scan AS veces_usado,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamano,
    pg_get_indexdef(s.indexrelid) AS definicion
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
ORDER BY s.relname, s.idx_scan ASC;

\echo ''
\echo '========================================================================='
\echo '4. AUDITORÍA DE POLÍTICAS RLS (ROW LEVEL SECURITY) ACTIVAS'
\echo '========================================================================='
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
ORDER BY tablename, policyname;

\echo ''
\echo '========================================================================='
\echo '5. ESTADO DE EXTENSIÓN pg_stat_statements'
\echo '========================================================================='
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'pg_stat_statements';

\echo ''
\echo '========================================================================='
\echo '6. EXPLAIN (ANALYZE, BUFFERS) - KPI_SERVICE: PERSPECTIVA ACADÉMICA & NLP'
\echo '   (Origen: backend/services/kpi_service.py:70-87, 606-661, 718-750)'
\echo '========================================================================='
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    COALESCE(NULLIF(m.programa, ''), m.nombre_modulo, 'Programa General') AS programa,
    COUNT(fa.id_hecho_aca) AS evaluados,
    AVG(fa.nota_final) AS promedio_notas,
    COUNT(fa.id_hecho_aca) FILTER (WHERE fa.nota_final >= 71.0) AS aprobados,
    COUNT(fa.id_hecho_aca) FILTER (WHERE fa.nota_final <= 70.0) AS en_riesgo_academico,
    COUNT(fa.id_hecho_aca) FILTER (WHERE fa.incumplimiento_actividades_pct > 30.0) AS en_riesgo_desercion,
    AVG(fa.nivel_confianza_ia) AS confianza_media_beto,
    COUNT(fa.id_hecho_aca) FILTER (WHERE fa.nivel_confianza_ia >= 0.85) AS extracciones_automaticas
FROM public.fact_rendimiento_academico fa
LEFT JOIN public.dim_modulo m ON fa.id_modulo = m.id_modulo
JOIN public.dim_tiempo t ON fa.id_tiempo = t.id_tiempo
WHERE fa.nota_final IS NOT NULL
GROUP BY COALESCE(NULLIF(m.programa, ''), m.nombre_modulo, 'Programa General');

\echo ''
\echo '========================================================================='
\echo '7. EXPLAIN (ANALYZE, BUFFERS) - KPI_SERVICE: PERSPECTIVA FINANCIERA'
\echo '   (Origen: backend/services/kpi_service.py:155-169, 225-235, 510-520)'
\echo '========================================================================='
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    ff.estado_cartera,
    COUNT(ff.id_hecho_fin) AS total_registros,
    COUNT(DISTINCT ff.id_estudiante) AS alumnos_distintos,
    COALESCE(SUM(ff.monto_pagado), 0.0) AS total_recaudado_bs,
    COALESCE(SUM(ff.monto_deuda), 0.0) AS total_deuda_bs,
    COUNT(ff.id_hecho_fin) FILTER (WHERE ff.cuotas_impagas >= 2) AS registros_mora_2_cuotas
FROM public.fact_situacion_financiera ff
JOIN public.dim_tiempo t ON ff.id_tiempo = t.id_tiempo
GROUP BY ff.estado_cartera;

\echo ''
\echo '========================================================================='
\echo '8. EXPLAIN (ANALYZE, BUFFERS) - KPI_SERVICE: METAS & RENTABILIDAD'
\echo '   (Origen: backend/services/kpi_service.py:421-455)'
\echo '========================================================================='
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    t.periodo_mes,
    SUM(fr.monto_ejecutado) AS ejecutado,
    SUM(fr.monto_meta) AS meta
FROM public.fact_rentabilidad fr
JOIN public.dim_tiempo t ON fr.id_tiempo = t.id_tiempo
GROUP BY t.periodo_mes
ORDER BY t.periodo_mes DESC;

\echo ''
\echo '========================================================================='
\echo '9. EXPLAIN (ANALYZE, BUFFERS) - CONSULTA PROPUESTA SQL PARA ALERTAS A/D/F'
\echo '   (Reemplaza las 7 consultas .all() en backend/services/risk_service.py:109-187)'
\echo '   Preserva reglas exactas: promedio <= 70, incumplimiento > 30%, cuotas >= 2'
\echo '========================================================================='
EXPLAIN (ANALYZE, BUFFERS)
WITH acad_agg AS (
    SELECT
        fa.id_estudiante,
        ROUND(AVG(fa.nota_final)::numeric, 1) AS promedio_notas,
        ROUND(MIN(fa.asistencia_pct)::numeric, 1) AS asistencia_min_pct,
        ROUND(
            MAX(
                GREATEST(
                    COALESCE(fa.incumplimiento_actividades_pct, 0.0),
                    CASE
                        WHEN fa.asistencia_pct IS NOT NULL
                        THEN GREATEST(0.0, 100.0 - fa.asistencia_pct)
                        ELSE 0.0
                    END
                )
            )::numeric,
            1
        ) AS max_incumplimiento_pct,
        BOOL_OR(UPPER(COALESCE(fa.tipo_alerta, '')) = 'DESERCION') AS alerta_desercion_explicita
    FROM public.fact_rendimiento_academico fa
    WHERE fa.id_estudiante IS NOT NULL
    GROUP BY fa.id_estudiante
),
fin_agg AS (
    SELECT
        ff.id_estudiante,
        COALESCE(SUM(ff.cuotas_impagas), 0) AS cuotas_mora,
        ROUND(
            COALESCE(
                SUM(
                    CASE
                        WHEN COALESCE(ff.cuotas_impagas, 0) > 0 OR COALESCE(ff.monto_deuda, 0) > 0
                        THEN COALESCE(ff.monto_deuda, 0.0)
                        ELSE 0.0
                    END
                ),
                0.0
            )::numeric,
            2
        ) AS deuda_mora_bs
    FROM public.fact_situacion_financiera ff
    WHERE ff.id_estudiante IS NOT NULL
    GROUP BY ff.id_estudiante
)
SELECT
    e.id_estudiante,
    COALESCE(e.ci, e.ci_numero, e.codigo_estudiante, 'S/C') AS ci,
    e.nombre_completo,
    COALESCE(e.programa_origen, 'Programa General') AS programa,
    a.promedio_notas,
    COALESCE(a.max_incumplimiento_pct, 0.0) AS incumplimiento_pct,
    a.asistencia_min_pct AS asistencia_pct,
    COALESCE(f.cuotas_mora, 0) AS cuotas_mora,
    COALESCE(f.deuda_mora_bs, 0.0) AS deuda_mora_bs,
    (a.promedio_notas IS NOT NULL AND a.promedio_notas <= 70.0) AS regla_academico,
    (COALESCE(a.max_incumplimiento_pct, 0.0) > 30.0 OR COALESCE(a.alerta_desercion_explicita, FALSE)) AS regla_desercion,
    (COALESCE(f.cuotas_mora, 0) >= 2) AS regla_financiero
FROM public.dim_estudiante e
LEFT JOIN acad_agg a ON a.id_estudiante = e.id_estudiante
LEFT JOIN fin_agg f ON f.id_estudiante = e.id_estudiante
WHERE e.deprecado = FALSE
  AND (
      (a.promedio_notas IS NOT NULL AND a.promedio_notas <= 70.0)
      OR (COALESCE(a.max_incumplimiento_pct, 0.0) > 30.0 OR COALESCE(a.alerta_desercion_explicita, FALSE))
      OR (COALESCE(f.cuotas_mora, 0) >= 2)
  );

\echo ''
\echo '========================================================================='
\echo '10. EXPLAIN (ANALYZE, BUFFERS) - FICHA CRUZADA DE ESTUDIANTE INDIVIDUAL'
\echo '    (Origen: backend/services/risk_service.py:586-661)'
\echo '========================================================================='
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    fa.id_hecho_aca,
    fa.id_estudiante,
    fa.id_modulo,
    fa.nota_final,
    fa.asistencia_pct,
    fa.incumplimiento_actividades_pct,
    fa.estado_academico,
    m.nombre_modulo,
    m.programa,
    m.pos_code,
    d.nombre_completo AS docente,
    t.gestion,
    t.periodo_mes,
    o.nombre_archivo,
    o.hash_sha256
FROM public.fact_rendimiento_academico fa
LEFT JOIN public.dim_modulo m ON fa.id_modulo = m.id_modulo
LEFT JOIN public.dim_docente d ON fa.id_docente = d.id_docente
LEFT JOIN public.dim_tiempo t ON fa.id_tiempo = t.id_tiempo
LEFT JOIN public.dim_origen_documental o ON fa.id_documento = o.id_documento
WHERE fa.id_estudiante = 1
ORDER BY fa.id_hecho_aca DESC;
