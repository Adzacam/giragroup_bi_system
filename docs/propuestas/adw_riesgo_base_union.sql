-- 023 (ADW): bi.vw_riesgo_estudiante parte de la UNION de estudiantes con registro academico o financiero por gestion.
-- Antes solo partia de los academicos: 2026 (sin datos academicos) quedaba vacia y la regla financiera (DA3) solo veia
-- 249 estudiantes frente a los 1.4xx de la pantalla de Alertas. Sin DROP; mismas columnas y orden; CREATE OR REPLACE.
-- Va despues de 022 (DA3: en mora = algun hecho con cuotas_impagas >= 2). NO aplicar a la DW viva sin decision de Lean (FU-L9).
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
