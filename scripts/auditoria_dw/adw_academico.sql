-- ADW L0 · bloque académico (A2, A6, D1): cobertura, asistencia, incumplimiento y confianza por gestión
SELECT t.gestion, count(*) AS filas, count(DISTINCT a.id_estudiante) AS estudiantes,
       count(a.asistencia_pct) AS con_asistencia,
       count(*) FILTER (WHERE a.incumplimiento_actividades_pct = 0) AS incumplimiento_cero,
       count(a.incumplimiento_actividades_pct) AS con_incumplimiento,
       round(avg(a.nivel_confianza_ia)::numeric, 3) AS confianza_media,
       round(100.0 * count(*) FILTER (WHERE a.nivel_confianza_ia > 0.85) / count(*), 2) AS pct_conf_mayor_085,
       count(*) FILTER (WHERE a.requiere_revision) AS requiere_revision
FROM public.fact_rendimiento_academico a
JOIN public.dim_tiempo t ON t.id_tiempo = a.id_tiempo
GROUP BY 1
ORDER BY 1;
