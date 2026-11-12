BEGIN;
-- No reconstruir captación a partir de inscripciones ni alterar contadores históricos.
ALTER TABLE public.fact_marketing ADD COLUMN IF NOT EXISTS leads_captacion INTEGER;
ALTER TABLE public.fact_marketing ADD COLUMN IF NOT EXISTS inscritos_captacion INTEGER;

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
), rent AS (   -- ingresos por mes; un mes cuenta como ejecutado si tiene ingreso > 0
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
), yoy AS (    -- solo meses ejecutados en la gestión actual: compara periodos equivalentes
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
UNION ALL SELECT gestion, 'KPI-22', inscritos FROM convenio;

UPDATE bi.ref_kpi SET descripcion = 'Inscritos sobre interesados informados en la misma fuente de captación. Sin dato cuando no hay cifras comprobables.' WHERE codigo = 'KPI-06';
INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('014_conversion_captacion_comprobable.sql', now())
ON CONFLICT (version) DO NOTHING;
COMMIT;
