-- =============================================================================
-- 026 · FU-L6 Metas: granularidad MENSUAL / ANUAL de la meta (DA4), prioridad por tipo de fuente (DA-FU3) y mes parcial
-- =============================================================================
-- DA4 (decisión de Lean, 2026-11-20): el cargador marca la granularidad de cada meta según la FORMA de la fuente (una sola celda anual
--   = ANUAL; no se coloca en diciembre). KPI-02 solo se calcula con meta MENSUAL: sin meta mensual en la gestión queda «sin dato» (NULL).
--   KPI-03, KPI-13 y KPI-14 usan la meta anual (mensual + anual) de la gestión. Una fila sin bandera (anterior a la 026) se lee como MENSUAL.
-- Mes parcial: la fecha de corte de la fuente es el último mes con ejecutado de toda la tabla; ese mes (salvo diciembre) es parcial y
--   KPI-02, KPI-03 y KPI-12 solo usan meses cerrados. KPI-13 y KPI-14 siguen con el ejecutado acumulado completo.
-- Cambios: una columna nueva (nullable, con CHECK) en fact_rentabilidad y dos vistas redefinidas (bi.vw_cmi_valores desde la 025 y
--   bi.vw_metas_mensual desde la 006; esta última agrega meta_anual al final). Ninguna tabla ni vista nueva (siguen 51 tablas + 10 vistas bi).
--   Idempotente (ADD COLUMN IF NOT EXISTS, CREATE OR REPLACE VIEW) y no destructiva (sin DROP de datos).
-- Requiere la 022 a la 025 aplicadas antes (la vista parte de la definición de la 025). Las filas que ya existen quedan con granularidad
--   NULL (MENSUAL): una recarga del libro de metas las marca (decisión de Lean: las migraciones 022-026 se aplican a la DW viva en FU-L9).
BEGIN;

ALTER TABLE public.fact_rentabilidad
    ADD COLUMN IF NOT EXISTS granularidad_meta VARCHAR(10);
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fact_rentabilidad_granularidad_meta') THEN
        ALTER TABLE public.fact_rentabilidad
            ADD CONSTRAINT chk_fact_rentabilidad_granularidad_meta
            CHECK (granularidad_meta IS NULL OR granularidad_meta IN ('MENSUAL', 'ANUAL'));
    END IF;
END $$;
COMMENT ON COLUMN public.fact_rentabilidad.granularidad_meta IS
    'FU-L6 (DA4): MENSUAL = meta de ese mes; ANUAL = una sola celda de la gestion (no es la meta de ningun mes). NULL = anterior a la 026 (se lee como MENSUAL).';

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
    -- FU-L6 (DA4): la meta se separa por granularidad. NULL se lee como MENSUAL (filas anteriores a la 026 o sin perfil de hoja).
    -- Una meta ANUAL (una sola celda de la gestión) no es la meta de ningún mes: solo cuenta en la meta anual.
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
    -- Fecha de corte de la fuente, derivada del contenido: el último mes con ejecutado de todas las gestiones.
    SELECT MAX(gestion * 100 + mes) AS aaaamm FROM rent WHERE ejecutado > 0
), rent_c AS (
    -- Mes cerrado: mes con ejecutado, salvo el mes de corte, que es parcial (la fuente se cortó dentro del mes) a menos que sea diciembre.
    SELECT r.*, (r.ejecutado > 0 AND (r.gestion * 100 + r.mes <> c.aaaamm OR r.mes = 12)) AS cerrado
    FROM rent r CROSS JOIN corte c
), rent_g AS (
    SELECT gestion,
           SUM(ejecutado)                                                    AS ejecutado,
           SUM(ejecutado) FILTER (WHERE cerrado)                             AS ejecutado_cerrado,
           SUM(meta_mensual) + SUM(meta_anual_celda)                         AS meta_anual,
           -- KPI-03: meta mensual de los meses cerrados + la meta anual completa (una meta anual no se prorratea)
           COALESCE(SUM(meta_mensual) FILTER (WHERE cerrado), 0) + SUM(meta_anual_celda) AS meta_a_la_fecha,
           MAX(mes)  FILTER (WHERE cerrado)                                  AS ultimo_mes
    FROM rent_c GROUP BY gestion
), ult_mes AS (
    -- KPI-02: último mes cerrado frente a la meta MENSUAL de ese mes; sin meta mensual (solo anual o ninguna) queda sin dato
    SELECT r.gestion, 100.0 * r.ejecutado / NULLIF(r.meta_mensual, 0) AS cumpl_mes
    FROM rent_c r JOIN rent_g g ON g.gestion = r.gestion AND g.ultimo_mes = r.mes
), yoy AS (
    -- KPI-12: meses cerrados de la gestión frente a los mismos meses de la anterior (el mes parcial no se compara con uno completo)
    SELECT c.gestion, 100.0 * (SUM(c.ejecutado) / NULLIF(SUM(p.ejecutado), 0) - 1) AS var_pct
    FROM rent_c c
    JOIN rent p ON p.gestion = c.gestion - 1 AND p.mes = c.mes
    WHERE c.cerrado
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

-- Ingresos vs meta por mes (página Financiera): la meta mensual solo suma metas MENSUALES; la meta anual va en una columna aparte (al final,
-- así CREATE OR REPLACE VIEW conserva las columnas existentes). Una meta anual ya no aparece como meta de diciembre.
CREATE OR REPLACE VIEW bi.vw_metas_mensual AS
WITH base AS (
    SELECT dt.gestion, dt.mes, MIN(dt.nombre_mes) AS nombre_mes,
           dc.nombre_categoria AS categoria,
           SUM(fr.monto_ejecutado) AS ejecutado,
           SUM(fr.monto_meta) FILTER (WHERE COALESCE(fr.granularidad_meta, 'MENSUAL') = 'MENSUAL') AS meta,
           SUM(fr.monto_meta) FILTER (WHERE fr.granularidad_meta = 'ANUAL')                       AS meta_anual
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt               ON dt.id_tiempo = fr.id_tiempo
    JOIN public.dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria
    WHERE dc.tipo = 'INGRESO'
    GROUP BY dt.gestion, dt.mes, dc.nombre_categoria
)
SELECT b.gestion, b.mes, b.nombre_mes, b.categoria, b.ejecutado, b.meta,
       make_date(b.gestion, b.mes, 1)                                   AS fecha_mes,
       ROUND(100 * b.ejecutado / NULLIF(b.meta, 0), 2)                  AS avance_pct,
       LAG(b.ejecutado) OVER w                                          AS ejecutado_anio_ant,
       b.meta_anual
FROM base b
WINDOW w AS (PARTITION BY b.categoria, b.mes ORDER BY b.gestion);

UPDATE bi.ref_kpi SET descripcion = 'Ingreso ejecutado del último mes cerrado frente a la meta MENSUAL de ese mes. Sin dato si la fuente solo trae meta anual o ninguna (DA4); el mes de corte de la fuente es parcial y no cuenta.'
 WHERE codigo = 'KPI-02';
UPDATE bi.ref_kpi SET descripcion = 'Ingreso ejecutado de los meses cerrados frente a la meta de esos meses; con meta anual, frente a la meta anual completa (DA4).'
 WHERE codigo = 'KPI-03';
UPDATE bi.ref_kpi SET descripcion = 'Ingreso de los meses cerrados de la gestión frente a los mismos meses de la gestión anterior; el mes de corte parcial no se compara.'
 WHERE codigo = 'KPI-12';

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('026_fu_l6_metas_granularidad.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
