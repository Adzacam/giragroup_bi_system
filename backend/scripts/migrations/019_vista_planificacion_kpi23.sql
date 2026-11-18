-- =============================================================================
-- 019 · Vista bi.vw_planificacion_ejecucion_mensual y KPI-23 (Diseño B, V-4)
-- =============================================================================
BEGIN;

INSERT INTO bi.ref_kpi (
    codigo, perspectiva, nombre, descripcion, unidad, sentido,
    meta, umbral_verde, umbral_ambar, orden
) VALUES (
    'KPI-23',
    'PROCESOS_INTERNOS',
    'Cumplimiento de inicios planificados',
    'Porcentaje de programas planificados con estado conocido que iniciaron, agrupados por POS y mes.',
    'PCT',
    'MAX',
    85,
    85,
    60,
    23
)
ON CONFLICT (codigo) DO UPDATE SET
    perspectiva = EXCLUDED.perspectiva,
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    unidad = EXCLUDED.unidad,
    sentido = EXCLUDED.sentido,
    meta = EXCLUDED.meta,
    umbral_verde = EXCLUDED.umbral_verde,
    umbral_ambar = EXCLUDED.umbral_ambar,
    orden = EXCLUDED.orden,
    activo = TRUE;

CREATE OR REPLACE VIEW bi.vw_planificacion_ejecucion_mensual AS
WITH por_programa_mes AS (
    SELECT
        fp.id_tiempo_plan,
        COALESCE(NULLIF(upper(btrim(fp.pos_code_fuente)), ''), 'ORIGEN:' || fp.clave_fila_origen) AS programa_mes,
        NULLIF(upper(btrim(max(fp.pos_code_fuente))), '') AS pos_code,
        bool_or(fp.estado_fuente IN ('Inicio Confirmado', 'En curso', 'Finalizo')) AS iniciado,
        bool_or(fp.estado_fuente IN ('Por iniciar', 'Inicio Confirmado', 'En curso', 'Finalizo')) AS planificado,
        bool_or(fp.estado_fuente = 'Finalizo') AS finalizado,
        bool_or(fp.estado_fuente = 'Baja') AS baja,
        bool_or(fp.estado_fuente = 'Reprogramado') AS reprogramado,
        MAX(fp.costo_programa) AS costo_programa,
        MAX(fp.pauta_asignada) AS pauta_asignada,
        MAX(fp.pauta_ejecutada) AS pauta_ejecutada
    FROM public.fact_planificacion_programa fp
    WHERE fp.id_tiempo_plan IS NOT NULL
    GROUP BY fp.id_tiempo_plan,
             COALESCE(NULLIF(upper(btrim(fp.pos_code_fuente)), ''), 'ORIGEN:' || fp.clave_fila_origen)
), agg_prog AS (
    SELECT
        p.id_tiempo_plan AS id_tiempo,
        COUNT(*) FILTER (WHERE p.planificado) AS programas_planificados,
        COUNT(*) FILTER (WHERE p.iniciado) AS programas_iniciados,
        COUNT(*) FILTER (WHERE p.finalizado) AS programas_finalizados,
        COUNT(*) FILTER (WHERE p.baja) AS programas_baja,
        COUNT(*) FILTER (WHERE p.reprogramado) AS programas_reprogramados,
        COUNT(DISTINCT p.pos_code) AS programas_con_pos,
        COALESCE(SUM(p.costo_programa), 0) AS costo_programa,
        COALESCE(SUM(p.pauta_asignada), 0) AS pauta_asignada,
        COALESCE(SUM(p.pauta_ejecutada), 0) AS pauta_ejecutada
    FROM por_programa_mes p
    GROUP BY p.id_tiempo_plan
), cob_estado AS (
    SELECT
        fp.id_tiempo_plan AS id_tiempo,
        100.0 * COUNT(*) FILTER (WHERE NULLIF(btrim(fp.estado_fuente), '') IS NOT NULL)
            / NULLIF(COUNT(*), 0) AS cobertura_estado
    FROM public.fact_planificacion_programa fp
    WHERE fp.id_tiempo_plan IS NOT NULL
    GROUP BY fp.id_tiempo_plan
), metas_plan AS (
    SELECT
        dm.id_tiempo,
        MAX(dm.monto_meta) FILTER (WHERE dm.categoria = 'PLAN_INGRESO_TOTAL') AS meta_ingreso_total,
        MAX(dm.monto_meta) FILTER (WHERE dm.categoria = 'PLAN_INGRESO_TECHOS_PROYECTADO') AS ingreso_proyectado_techos,
        MAX(dm.monto_meta) FILTER (WHERE dm.categoria = 'OKR_APERTURAS' AND (dm.tipo_programa IS NULL OR dm.tipo_programa = 'TOTAL')) AS meta_aperturas_okr
    FROM public.dim_meta dm
    WHERE dm.id_tiempo IS NOT NULL
    GROUP BY dm.id_tiempo
), fin_fuente AS (
    SELECT
        fr.id_tiempo,
        SUM(fr.monto_meta) AS meta_financiera,
        SUM(fr.monto_ejecutado) AS ejecutado_financiero
    FROM public.fact_rentabilidad fr
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO' AND fr.id_tiempo IS NOT NULL
    GROUP BY fr.id_tiempo
), periodos AS (
    SELECT id_tiempo FROM agg_prog
    UNION
    SELECT id_tiempo FROM metas_plan
    UNION
    SELECT id_tiempo FROM fin_fuente
)
SELECT
    dt.gestion,
    dt.mes,
    pe.id_tiempo,
    COALESCE(ap.programas_planificados, 0) AS programas_planificados,
    COALESCE(ap.programas_iniciados, 0) AS programas_iniciados,
    COALESCE(ap.programas_finalizados, 0) AS programas_finalizados,
    COALESCE(ap.programas_baja, 0) AS programas_baja,
    COALESCE(ap.programas_reprogramados, 0) AS programas_reprogramados,
    100.0 * ap.programas_iniciados / NULLIF(ap.programas_planificados, 0) AS kpi_23,
    ce.cobertura_estado,
    COALESCE(ap.programas_con_pos, 0) AS programas_con_pos,
    mp.meta_ingreso_total,
    mp.ingreso_proyectado_techos,
    mp.meta_aperturas_okr,
    ff.meta_financiera,
    ff.ejecutado_financiero,
    COALESCE(ap.costo_programa, 0) AS costo_programa,
    COALESCE(ap.pauta_asignada, 0) AS pauta_asignada,
    COALESCE(ap.pauta_ejecutada, 0) AS pauta_ejecutada
FROM periodos pe
JOIN public.dim_tiempo dt ON dt.id_tiempo = pe.id_tiempo
LEFT JOIN agg_prog ap ON ap.id_tiempo = pe.id_tiempo
LEFT JOIN cob_estado ce ON ce.id_tiempo = pe.id_tiempo
LEFT JOIN metas_plan mp ON mp.id_tiempo = pe.id_tiempo
LEFT JOIN fin_fuente ff ON ff.id_tiempo = pe.id_tiempo
ORDER BY dt.gestion, dt.mes;

CREATE OR REPLACE VIEW bi.vw_cmi_valores AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante, ra.nota_final, ra.nivel_confianza_ia,
           GREATEST(COALESCE(ra.incumplimiento_actividades_pct,0),
                    GREATEST(0, 100 - COALESCE(ra.asistencia_pct,100))) AS incumplimiento_ef
    FROM public.fact_rendimiento_academico ra
    JOIN public.dim_tiempo dt ON dt.id_tiempo = ra.id_tiempo
), fin AS (
    SELECT dt.gestion, sf.id_estudiante, sf.monto_pagado, sf.monto_deuda,
           sf.cuotas_impagas, sf.estado_cartera
    FROM public.fact_situacion_financiera sf
    JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
), rent AS (
    SELECT dt.gestion, dt.mes,
           COALESCE(SUM(fr.monto_ejecutado), 0) AS ejecutado,
           COALESCE(SUM(fr.monto_meta), 0)      AS meta
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, dt.mes
), rent_g AS (
    SELECT gestion,
           SUM(ejecutado)                               AS ejecutado,
           SUM(meta)                                    AS meta_anual,
           SUM(meta) FILTER (WHERE ejecutado > 0)       AS meta_a_la_fecha,
           MAX(mes)  FILTER (WHERE ejecutado > 0)       AS ultimo_mes
    FROM rent GROUP BY gestion
), ult_mes AS (
    SELECT r.gestion, 100.0 * r.ejecutado / NULLIF(r.meta, 0) AS cumpl_mes
    FROM rent r JOIN rent_g g ON g.gestion = r.gestion AND g.ultimo_mes = r.mes
), yoy AS (
    SELECT c.gestion, 100.0 * (SUM(c.ejecutado) / NULLIF(SUM(p.ejecutado), 0) - 1) AS var_pct
    FROM rent c
    JOIN rent p ON p.gestion = c.gestion - 1 AND p.mes = c.mes
    WHERE c.ejecutado > 0
    GROUP BY c.gestion
), aca_g AS (
    SELECT gestion,
           COUNT(DISTINCT id_estudiante)                                      AS matricula,
           AVG(nota_final)                                                    AS promedio,
           100.0 * COUNT(*) FILTER (WHERE nota_final >= 70) / NULLIF(COUNT(nota_final),0) AS aprobacion,
           AVG(nivel_confianza_ia) * 100                                      AS confianza,
           100.0 * COUNT(*) FILTER (WHERE nivel_confianza_ia >= 0.85)
                 / NULLIF(COUNT(nivel_confianza_ia),0)                        AS automatizacion,
           100.0 * COUNT(DISTINCT id_estudiante) FILTER (WHERE incumplimiento_ef > 30)
                 / NULLIF(COUNT(DISTINCT id_estudiante),0)                    AS desercion
    FROM aca GROUP BY gestion
), riesgo_g AS (
    SELECT gestion,
           COUNT(*) FILTER (WHERE regla_a_academico = 1) AS riesgo_aca,
           COUNT(*) FILTER (WHERE k_reglas >= 2)         AS criticos
    FROM bi.vw_riesgo_estudiante GROUP BY gestion
), fin_g AS (
    SELECT gestion,
           SUM(monto_pagado)                                                  AS recaudacion,
           COUNT(DISTINCT id_estudiante)                                      AS pagantes,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE cuotas_impagas >= 2
                                   OR estado_cartera = 'Previsionable')       AS riesgo_fin,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera = 'Vigente')               AS n_v,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera IN ('Mora','En Mora'))     AS n_m,
           COUNT(DISTINCT id_estudiante) FILTER (WHERE estado_cartera = 'Previsionable')         AS n_p,
           100.0 * SUM(monto_deuda) FILTER (WHERE estado_cartera IN ('Mora','En Mora','Previsionable'))
                 / NULLIF(SUM(monto_deuda),0)                                 AS cartera_vencida
    FROM fin GROUP BY gestion
), mkt AS (
    SELECT dt.gestion, 100.0 * SUM(fm.inscritos_captacion) / NULLIF(SUM(fm.leads_captacion),0) AS conversion
    FROM public.fact_marketing fm JOIN public.dim_tiempo dt ON dt.id_tiempo = fm.id_tiempo
    WHERE fm.leads_captacion > 0 AND fm.inscritos_captacion >= 0
      AND fm.inscritos_captacion <= fm.leads_captacion GROUP BY dt.gestion
), eval AS (
    SELECT dt.gestion,
           AVG(100.0 * ev.puntuacion / NULLIF(ev.escala_max,0)) FILTER (WHERE ev.tipo_pregunta = 'DOCENTE')       AS sat_docente,
           AVG(100.0 * ev.puntuacion / NULLIF(ev.escala_max,0)) FILTER (WHERE ev.tipo_pregunta = 'INSTITUCIONAL') AS sat_institucional
    FROM public.fact_evaluacion_docente ev JOIN public.dim_tiempo dt ON dt.id_tiempo = ev.id_tiempo
    GROUP BY dt.gestion
), convenio AS (
    SELECT gestion, SUM(n_inscritos) AS inscritos
    FROM public.fact_techo_convenio WHERE gestion IS NOT NULL GROUP BY gestion
), backlog AS (
    SELECT EXTRACT(YEAR FROM created_at)::int AS gestion, COUNT(*) AS n
    FROM public.stg_entidad_no_resuelta WHERE resuelto = FALSE
    GROUP BY 1
), plan_pm AS (
    SELECT dt.gestion,
           fp.id_tiempo_plan,
           COALESCE(NULLIF(upper(btrim(fp.pos_code_fuente)), ''), 'ORIGEN:' || fp.clave_fila_origen) AS programa_mes,
           bool_or(fp.estado_fuente IN ('Inicio Confirmado', 'En curso', 'Finalizo')) AS iniciado,
           bool_or(fp.estado_fuente IN ('Por iniciar', 'Inicio Confirmado', 'En curso', 'Finalizo')) AS planificado
    FROM public.fact_planificacion_programa fp
    JOIN public.dim_tiempo dt ON dt.id_tiempo = fp.id_tiempo_plan
    GROUP BY dt.gestion, fp.id_tiempo_plan,
             COALESCE(NULLIF(upper(btrim(fp.pos_code_fuente)), ''), 'ORIGEN:' || fp.clave_fila_origen)
), plan AS (
    SELECT gestion,
           100.0 * COUNT(*) FILTER (WHERE iniciado) / NULLIF(COUNT(*) FILTER (WHERE planificado), 0) AS kpi_23
    FROM plan_pm
    GROUP BY gestion
)
SELECT f.gestion, 'KPI-01'::varchar(10) AS codigo,
       f.recaudacion / NULLIF(COALESCE(NULLIF(a.matricula,0), f.pagantes),0) AS valor
  FROM fin_g f LEFT JOIN aca_g a USING (gestion)
UNION ALL SELECT gestion, 'KPI-02', cumpl_mes FROM ult_mes
UNION ALL SELECT gestion, 'KPI-03', 100.0 * ejecutado / NULLIF(meta_a_la_fecha,0) FROM rent_g
UNION ALL SELECT gestion, 'KPI-04', riesgo_fin FROM fin_g
UNION ALL SELECT gestion, 'KPI-05', 100.0 * (n_m + n_p) / NULLIF(n_v + n_m + n_p,0) FROM fin_g
UNION ALL SELECT gestion, 'KPI-06', conversion FROM mkt
UNION ALL SELECT gestion, 'KPI-07', promedio FROM aca_g
UNION ALL SELECT gestion, 'KPI-08', aprobacion FROM aca_g
UNION ALL SELECT gestion, 'KPI-09', riesgo_aca FROM riesgo_g
UNION ALL SELECT gestion, 'KPI-10', confianza FROM aca_g
UNION ALL SELECT gestion, 'KPI-11', automatizacion FROM aca_g
UNION ALL SELECT gestion, 'KPI-12', var_pct FROM yoy
UNION ALL SELECT gestion, 'KPI-13', 100.0 * ejecutado / NULLIF(meta_anual,0) FROM rent_g
UNION ALL SELECT gestion, 'KPI-14', GREATEST(meta_anual - ejecutado, 0) FROM rent_g WHERE meta_anual > 0
UNION ALL SELECT gestion, 'KPI-15', cartera_vencida FROM fin_g
UNION ALL SELECT gestion, 'KPI-16', desercion FROM aca_g
UNION ALL SELECT gestion, 'KPI-17', criticos FROM riesgo_g
UNION ALL SELECT gestion, 'KPI-18', n FROM backlog
UNION ALL SELECT gestion, 'KPI-19', sat_docente FROM eval
UNION ALL SELECT gestion, 'KPI-20', sat_institucional FROM eval
UNION ALL SELECT gestion, 'KPI-21', matricula FROM aca_g
UNION ALL SELECT gestion, 'KPI-22', inscritos FROM convenio
UNION ALL SELECT gestion, 'KPI-23', kpi_23 FROM plan;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('019_vista_planificacion_kpi23.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
