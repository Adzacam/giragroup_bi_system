-- =============================================================================
-- 028 · FU-L9 + ADW-L9 Decisiones escritas de Lean (2026-11-21):
--   1. KPI-01 (A7): pagantes como denominador único para todos los años (2023–2026)
--      en bi.vw_cmi_valores.
--   2. Riesgo estudiantil (52ecec0): bi.vw_riesgo_estudiante = UNION de estudiantes
--      con registro académico o financiero por gestión; regla_a_academico y
--      regla_d_desercion quedan NULL cuando no hay registro académico.
--   3. Guarda NULL en riesgo_g de bi.vw_cmi_valores (KPI-09 y KPI-17) cuando no
--      hay registros académicos en la gestión (ej. 2026 -> sin dato, no 0).
--   4. DA5: mantiene los 9 KPI sin umbral en NULL y KPI-13 sin cambios.
--   5. Encuestas (FU-L5): NPS sigue solo informativo (23 KPI en bi.ref_kpi).
-- =============================================================================
-- Idempotente (CREATE OR REPLACE VIEW) y no destructiva. Mantiene intactos:
-- 51 tablas + 10 vistas bi + 23 KPI en bi.ref_kpi.
-- Requiere 022..027 aplicadas antes.
BEGIN;

CREATE OR REPLACE VIEW bi.vw_riesgo_estudiante AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante,
           AVG(ra.nota_final) AS prom_notas,
           MAX(GREATEST(COALESCE(ra.incumplimiento_actividades_pct, 0),
                        GREATEST(0, 100 - COALESCE(ra.asistencia_pct, 100)))) AS max_incumplimiento_pct
    FROM public.fact_rendimiento_academico ra
    JOIN public.dim_tiempo dt ON dt.id_tiempo = ra.id_tiempo
    GROUP BY dt.gestion, ra.id_estudiante
), fin AS (
    SELECT dt.gestion, sf.id_estudiante,
           SUM(sf.cuotas_impagas)          AS total_cuotas_impagas,
           SUM(sf.monto_deuda)             AS deuda_total_bs,
           bool_or(sf.cuotas_impagas >= 2) AS en_mora
    FROM public.fact_situacion_financiera sf
    JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
    GROUP BY dt.gestion, sf.id_estudiante
), base AS (
    SELECT gestion, id_estudiante FROM aca
    UNION
    SELECT gestion, id_estudiante FROM fin
), reglas AS (
    SELECT b.gestion, e.id_estudiante,
           COALESCE(NULLIF(e.programa_origen, ''), 'Programa general') AS programa,
           a.prom_notas, a.max_incumplimiento_pct,
           COALESCE(f.total_cuotas_impagas, 0) AS total_cuotas_impagas,
           COALESCE(f.deuda_total_bs, 0)       AS deuda_total_bs,
           (a.prom_notas <= 70.0)::int                        AS regla_a_academico,   -- NULL sin registro academico: no es un 0
           (a.max_incumplimiento_pct > 30.0)::int             AS regla_d_desercion,
           COALESCE(f.en_mora, FALSE)::int                    AS regla_f_financiero
    FROM base b
    JOIN public.dim_estudiante e ON e.id_estudiante = b.id_estudiante AND e.deprecado = FALSE
    LEFT JOIN aca a ON a.id_estudiante = b.id_estudiante AND a.gestion = b.gestion
    LEFT JOIN fin f ON f.id_estudiante = b.id_estudiante AND f.gestion = b.gestion
)
SELECT r.*,
       COALESCE(r.regla_a_academico,0) + COALESCE(r.regla_d_desercion,0) + COALESCE(r.regla_f_financiero,0) AS k_reglas,
       CASE COALESCE(r.regla_a_academico,0) + COALESCE(r.regla_d_desercion,0) + COALESCE(r.regla_f_financiero,0)
            WHEN 0 THEN 'SIN_ALERTA' WHEN 1 THEN 'MODERADA' ELSE 'CRITICA' END AS nivel_prioridad
FROM reglas r;

CREATE OR REPLACE VIEW bi.vw_cmi_valores AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante, ra.nota_final, ra.nivel_confianza_ia,
           GREATEST(COALESCE(ra.incumplimiento_actividades_pct,0),
                    GREATEST(0, 100 - COALESCE(ra.asistencia_pct,100))) AS incumplimiento_ef,
           COALESCE(ra.resultado, CASE WHEN ra.nota_final >= 70 THEN 'APROBADO'
                                       WHEN ra.nota_final IS NOT NULL THEN 'REPROBADO' END) AS resultado_ef,
           (upper(translate(COALESCE(ra.estado_academico, ''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) IN ('DESERCION', 'ABANDONO')
            OR upper(translate(COALESCE(ra.estado_tutoria, ''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) IN ('DESERCION', 'ABANDONO')) AS es_desertor,
           COALESCE(ra.estado_de_fuente,
                    upper(translate(COALESCE(ra.estado_academico, ''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) IN ('DESERCION', 'ABANDONO')
                    OR upper(translate(COALESCE(ra.estado_tutoria, ''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) IN ('DESERCION', 'ABANDONO')) AS estado_en_fuente
    FROM public.fact_rendimiento_academico ra
    JOIN public.dim_tiempo dt ON dt.id_tiempo = ra.id_tiempo
), fin AS (
    SELECT dt.gestion, sf.id_estudiante, sf.monto_pagado, sf.monto_deuda,
           sf.cuotas_impagas, sf.estado_cartera
    FROM public.fact_situacion_financiera sf
    JOIN public.dim_tiempo dt ON dt.id_tiempo = sf.id_tiempo
), fin_est AS (
    SELECT gestion, id_estudiante,
           bool_or(cuotas_impagas >= 2)            AS en_mora,
           bool_or(cuotas_impagas IS NOT NULL)     AS con_cartera,
           SUM(monto_deuda)                        AS deuda
    FROM fin
    GROUP BY gestion, id_estudiante
), rent AS (
    SELECT dt.gestion, dt.mes,
           COALESCE(SUM(fr.monto_ejecutado), 0) AS ejecutado,
           COALESCE(SUM(fr.monto_meta) FILTER (WHERE COALESCE(fr.granularidad_meta, 'MENSUAL') = 'MENSUAL'), 0) AS meta_mensual,
           COALESCE(SUM(fr.monto_meta) FILTER (WHERE fr.granularidad_meta = 'ANUAL'), 0)                       AS meta_anual_celda
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, dt.mes
), corte AS (
    SELECT MAX(gestion * 100 + mes) AS aaaamm FROM rent WHERE ejecutado > 0
), rent_c AS (
    SELECT r.*, (r.ejecutado > 0 AND (r.gestion * 100 + r.mes <> c.aaaamm OR r.mes = 12)) AS cerrado
    FROM rent r CROSS JOIN corte c
), rent_g AS (
    SELECT gestion,
           SUM(ejecutado)                                                    AS ejecutado,
           SUM(ejecutado) FILTER (WHERE cerrado)                             AS ejecutado_cerrado,
           SUM(meta_mensual) + SUM(meta_anual_celda)                         AS meta_anual,
           COALESCE(SUM(meta_mensual) FILTER (WHERE cerrado), 0) + SUM(meta_anual_celda) AS meta_a_la_fecha,
           MAX(mes)  FILTER (WHERE cerrado)                                  AS ultimo_mes
    FROM rent_c GROUP BY gestion
), ult_mes AS (
    SELECT r.gestion, 100.0 * r.ejecutado / NULLIF(r.meta_mensual, 0) AS cumpl_mes
    FROM rent_c r JOIN rent_g g ON g.gestion = r.gestion AND g.ultimo_mes = r.mes
), yoy AS (
    SELECT c.gestion, 100.0 * (SUM(c.ejecutado) / NULLIF(SUM(p.ejecutado), 0) - 1) AS var_pct
    FROM rent_c c
    JOIN rent p ON p.gestion = c.gestion - 1 AND p.mes = c.mes
    WHERE c.cerrado
    GROUP BY c.gestion
), aca_g AS (
    SELECT gestion,
           COUNT(DISTINCT id_estudiante)                                      AS matricula,
           AVG(nota_final) FILTER (WHERE nota_final BETWEEN 0 AND 100
                                     AND COALESCE(resultado_ef, '') NOT IN ('INASISTENCIA', 'EXIMIDO', 'SIN_NOTA')) AS promedio,
           100.0 * COUNT(*) FILTER (WHERE resultado_ef = 'APROBADO')
                 / NULLIF(COUNT(*) FILTER (WHERE resultado_ef IN ('APROBADO', 'REPROBADO', 'INASISTENCIA')), 0) AS aprobacion,
           AVG(nivel_confianza_ia) * 100                                      AS confianza,
           100.0 * COUNT(*) FILTER (WHERE nivel_confianza_ia >= 0.85)
                 / NULLIF(COUNT(nivel_confianza_ia),0)                        AS automatizacion,
           CASE WHEN bool_or(estado_en_fuente)
                THEN 100.0 * COUNT(DISTINCT id_estudiante) FILTER (WHERE es_desertor)
                           / NULLIF(COUNT(DISTINCT id_estudiante), 0) END     AS desercion
    FROM aca GROUP BY gestion
), riesgo_g AS (
    -- Guarda NULL cuando no hay registros académicos en la gestión (ej. 2026 -> sin dato, no 0)
    SELECT gestion,
           CASE WHEN COUNT(prom_notas) = 0 THEN NULL
                ELSE COUNT(*) FILTER (WHERE regla_a_academico = 1) END AS riesgo_aca,
           CASE WHEN COUNT(prom_notas) = 0 THEN NULL
                ELSE COUNT(*) FILTER (WHERE k_reglas >= 2) END         AS criticos
    FROM bi.vw_riesgo_estudiante GROUP BY gestion
), fin_g AS (
    SELECT r.gestion, r.recaudacion, r.pagantes,
           c.riesgo_fin, c.n_cartera,
           100.0 * c.riesgo_fin / NULLIF(c.n_cartera, 0)       AS mora_pct,
           100.0 * c.deuda_mora / NULLIF(c.deuda_total, 0)     AS cartera_vencida
    FROM (SELECT gestion, SUM(monto_pagado) AS recaudacion, COUNT(DISTINCT id_estudiante) AS pagantes
          FROM fin GROUP BY gestion) r
    LEFT JOIN (SELECT gestion,
                      COUNT(*) FILTER (WHERE en_mora)                AS riesgo_fin,
                      COUNT(*) FILTER (WHERE con_cartera)            AS n_cartera,
                      SUM(deuda) FILTER (WHERE en_mora)              AS deuda_mora,
                      SUM(deuda) FILTER (WHERE con_cartera)          AS deuda_total
               FROM fin_est GROUP BY gestion) c USING (gestion)
), mkt AS (
    SELECT dt.gestion, 100.0 * SUM(fm.inscritos_captacion) / NULLIF(SUM(fm.leads_captacion),0) AS conversion
    FROM public.fact_marketing fm JOIN public.dim_tiempo dt ON dt.id_tiempo = fm.id_tiempo
    WHERE fm.leads_captacion > 0 AND fm.inscritos_captacion >= 0
      AND fm.inscritos_captacion <= fm.leads_captacion GROUP BY dt.gestion
), eval AS (
    SELECT dt.gestion,
           AVG(100.0 * ev.puntuacion / ev.escala_max) FILTER (WHERE ev.tipo_pregunta = 'DOCENTE')       AS sat_docente,
           AVG(100.0 * ev.puntuacion / ev.escala_max) FILTER (WHERE ev.tipo_pregunta = 'INSTITUCIONAL') AS sat_institucional
    FROM public.fact_evaluacion_docente ev JOIN public.dim_tiempo dt ON dt.id_tiempo = ev.id_tiempo
    WHERE ev.puntuacion IS NOT NULL AND ev.escala_max > 0
      AND ev.puntuacion >= 1 AND ev.puntuacion <= ev.escala_max
    GROUP BY dt.gestion
), convenio AS (
    SELECT gestion, SUM(n_inscritos) AS inscritos
    FROM public.fact_techo_convenio WHERE gestion IS NOT NULL GROUP BY gestion
), doc_gestion AS (
    SELECT id_documento, MAX(gestion) AS gestion
    FROM (
        SELECT f.id_documento, dt.gestion FROM public.fact_rendimiento_academico f JOIN public.dim_tiempo dt ON dt.id_tiempo = f.id_tiempo WHERE f.id_documento IS NOT NULL
        UNION ALL
        SELECT f.id_documento, dt.gestion FROM public.fact_evaluacion_docente f JOIN public.dim_tiempo dt ON dt.id_tiempo = f.id_tiempo WHERE f.id_documento IS NOT NULL
        UNION ALL
        SELECT f.id_documento, dt.gestion FROM public.fact_situacion_financiera f JOIN public.dim_tiempo dt ON dt.id_tiempo = f.id_tiempo WHERE f.id_documento IS NOT NULL
        UNION ALL
        SELECT f.id_documento, dt.gestion FROM public.fact_rentabilidad f JOIN public.dim_tiempo dt ON dt.id_tiempo = f.id_tiempo WHERE f.id_documento IS NOT NULL
    ) t
    GROUP BY id_documento
), backlog_raw AS (
    SELECT COALESCE(
               (regexp_match(
                   COALESCE(s.payload_json::text, '') || ' ' ||
                   COALESCE(r.texto_plano, '') || ' ' ||
                   COALESCE(r.hoja, '') || ' ' ||
                   COALESCE(s.texto_original, ''),
                   '\m(202[0-9])\M'
               ))[1]::int,
               dg.gestion,
               (regexp_match(COALESCE(d.periodo, ''), '\m(202[0-9])\M'))[1]::int
           ) AS gestion
    FROM public.stg_entidad_no_resuelta s
    LEFT JOIN public.staging_registros_crudos r ON r.id = s.registro_origen_id
    LEFT JOIN public.dim_origen_documental d ON d.id_documento = s.id_documento
    LEFT JOIN doc_gestion dg ON dg.id_documento = s.id_documento
    WHERE s.resuelto = FALSE
), backlog AS (
    SELECT gestion, COUNT(*) AS n
    FROM backlog_raw
    WHERE gestion IS NOT NULL
    GROUP BY gestion
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
-- KPI-01 (A7): pagantes como denominador único para todos los años (2023–2026)
SELECT f.gestion, 'KPI-01'::varchar(10) AS codigo,
       f.recaudacion / NULLIF(f.pagantes, 0) AS valor
  FROM fin_g f
UNION ALL SELECT gestion, 'KPI-02', cumpl_mes FROM ult_mes
UNION ALL SELECT gestion, 'KPI-03', 100.0 * ejecutado_cerrado / NULLIF(meta_a_la_fecha,0) FROM rent_g
UNION ALL SELECT gestion, 'KPI-04', riesgo_fin FROM fin_g
UNION ALL SELECT gestion, 'KPI-05', mora_pct FROM fin_g
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

UPDATE bi.ref_kpi
   SET descripcion = 'Recaudación total dividida entre estudiantes pagantes únicos en la gestión (denominador único 2023–2026).'
 WHERE codigo = 'KPI-01';

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('028_fu_l9_decisiones_lean.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
