-- =============================================================================
-- 025 · FU-L5 Encuestas: KPI-19 y KPI-20 cuentan solo puntuacion en [1, escala_max] (DA1)
-- =============================================================================
-- DA1 (decisión de Lean, 2026-11-20): fuera de escala o texto = NULL; cuenta solo puntuacion en [1, escala_max]. El cargador
--   (backend/services/encuesta_canonica.py) ya guarda esos valores como NULL, pero la vista también los filtra para que la cifra
--   no dependa de la recarga: una puntuación 0, mayor que escala_max o sin escala no suma al numerador ni al denominador.
--   El NPS (tipo_pregunta = 'NPS', 0-10) sigue aparte y no entra en KPI-19 ni en KPI-20.
-- Solo cambia el CTE `eval` de bi.vw_cmi_valores; el resto de la vista es la definición de la 024.
-- Sin cambios de esquema: ninguna tabla ni columna nueva (siguen 51 tablas + 10 vistas bi). Idempotente (CREATE OR REPLACE VIEW).
-- Requiere la 022, la 023 y la 024 aplicadas antes (la vista parte de la definición de la 024).
BEGIN;

CREATE OR REPLACE VIEW bi.vw_cmi_valores AS
WITH aca AS (
    SELECT dt.gestion, ra.id_estudiante, ra.nota_final, ra.nivel_confianza_ia,
           GREATEST(COALESCE(ra.incumplimiento_actividades_pct,0),
                    GREATEST(0, 100 - COALESCE(ra.asistencia_pct,100))) AS incumplimiento_ef,
           -- DA-FU2: resultado canónico del módulo; una fila anterior a la 024 (resultado NULL) se deduce de la nota
           COALESCE(ra.resultado, CASE WHEN ra.nota_final >= 70 THEN 'APROBADO'
                                       WHEN ra.nota_final IS NOT NULL THEN 'REPROBADO' END) AS resultado_ef,
           -- DA2-bis: Deserción o Abandono en el estado académico o en el de tutoría (sin mayúsculas ni acentos)
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
    -- DA3 por estudiante y gestión: en mora si algún hecho de situación tiene >= 2 cuotas impagas.
    -- Los pagos mensuales (cuotas NULL, FU-L2) no son cartera: solo suman a la recaudación.
    SELECT gestion, id_estudiante,
           bool_or(cuotas_impagas >= 2)            AS en_mora,
           bool_or(cuotas_impagas IS NOT NULL)     AS con_cartera,
           SUM(monto_deuda)                        AS deuda
    FROM fin
    GROUP BY gestion, id_estudiante
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
           -- KPI-07 (DA-FU2): solo notas numericas de 0 a 100 sin INASISTENCIA, EXIMIDO ni SIN_NOTA; un 0 real entra
           AVG(nota_final) FILTER (WHERE nota_final BETWEEN 0 AND 100
                                     AND COALESCE(resultado_ef, '') NOT IN ('INASISTENCIA', 'EXIMIDO', 'SIN_NOTA')) AS promedio,
           -- KPI-08 (DA-FU2): APROBADO / (APROBADO + REPROBADO + INASISTENCIA); EXIMIDO y SIN_NOTA quedan fuera
           100.0 * COUNT(*) FILTER (WHERE resultado_ef = 'APROBADO')
                 / NULLIF(COUNT(*) FILTER (WHERE resultado_ef IN ('APROBADO', 'REPROBADO', 'INASISTENCIA')), 0) AS aprobacion,
           AVG(nivel_confianza_ia) * 100                                      AS confianza,
           100.0 * COUNT(*) FILTER (WHERE nivel_confianza_ia >= 0.85)
                 / NULLIF(COUNT(nivel_confianza_ia),0)                        AS automatizacion,
           -- KPI-16 (DA2-bis): estudiantes con Deserción o Abandono sobre la matrícula de la gestión; si ninguna fuente de la
           -- gestión trae el estado académico, queda sin dato (NULL), nunca 0
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
                      COUNT(*) FILTER (WHERE en_mora)                AS riesgo_fin,   -- KPI-04 (DA3)
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
    -- DA1 (FU-L5): cuenta solo puntuacion en [1, escala_max]; un 0, un valor fuera de escala o sin escala es «sin respuesta»:
    -- no suma al numerador ni al denominador. El NPS (0-10) queda fuera de KPI-19 y KPI-20.
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

UPDATE bi.ref_kpi SET descripcion = 'Satisfacción docente: promedio de las respuestas con puntuación en [1, escala_max] (DA1); el 0 y «Sin Información» no cuentan.'
 WHERE codigo = 'KPI-19';
UPDATE bi.ref_kpi SET descripcion = 'Satisfacción institucional: promedio de las respuestas con puntuación en [1, escala_max] (DA1); el 0 y «Sin Información» no cuentan.'
 WHERE codigo = 'KPI-20';

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('025_fu_l5_encuestas_escala_da1.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
