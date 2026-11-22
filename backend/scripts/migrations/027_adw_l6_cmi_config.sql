-- =============================================================================
-- 027 · ADW-L6 Configuración CMI (parte no bloqueada por DA5):
--   1. KPI-18 asignado a la gestión del dato (sin usar stg_entidad_no_resuelta.created_at).
--   2. bi.vw_cmi_gestiones filtra gestiones residuales (< 10 KPI con dato o < 5 con umbral, ej. 2023).
-- =============================================================================
-- Idempotente (CREATE OR REPLACE VIEW) y no destructiva. Mantiene intactos:
-- 51 tablas + 10 vistas bi + 23 KPI en bi.ref_kpi.
-- Requiere 022..026 aplicadas antes. Metas/umbrales (DA5) y KPI-13 vs KPI-03 quedan pendientes de Lean.
BEGIN;

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
    SELECT gestion,
           COUNT(*) FILTER (WHERE regla_a_academico = 1) AS riesgo_aca,
           COUNT(*) FILTER (WHERE k_reglas >= 2)         AS criticos
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
    -- Gestión predominante por documento en los hechos cargados (fallback cuando el registro crudo no trae año)
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
    -- ADW-L6 (A8): asignar cada pendiente a la gestión del dato (payload/texto crudo/hoja -> hechos del documento -> periodo del documento), sin usar stg_entidad_no_resuelta.created_at
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
SELECT f.gestion, 'KPI-01'::varchar(10) AS codigo,
       f.recaudacion / NULLIF(COALESCE(NULLIF(a.matricula,0), f.pagantes),0) AS valor
  FROM fin_g f LEFT JOIN aca_g a USING (gestion)
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

-- ADW-L6 (A11): filtrar gestiones residuales con menos de 10 KPI con dato o menos de 5 con umbral (ej. 2023)
CREATE OR REPLACE VIEW bi.vw_cmi_gestiones AS
SELECT v.gestion,
       count(*) AS indicadores_con_dato
FROM bi.vw_cmi_valores v
JOIN bi.ref_kpi k ON k.codigo::text = v.codigo::text AND k.activo
WHERE v.valor IS NOT NULL
GROUP BY v.gestion
HAVING count(*) >= 10
   AND count(*) FILTER (WHERE k.umbral_verde IS NOT NULL) >= 5;

UPDATE bi.ref_kpi
   SET descripcion = 'Entidades pendientes de revisión humana en staging agrupadas por gestión del dato (sin depender de fecha de carga).'
 WHERE codigo = 'KPI-18';

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('027_adw_l6_cmi_config.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
