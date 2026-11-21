-- ADW L0 · bloque evaluación docente (A1, C2): puntuaciones en 0 o fuera de escala por documento y gestión
SELECT d.id_documento, d.nombre_archivo, d.tipo_fuente, d.tipo_escala, t.gestion, e.tipo_pregunta, e.escala_max,
       count(*) AS filas,
       count(*) FILTER (WHERE e.puntuacion = 0) AS puntuacion_cero,
       count(*) FILTER (WHERE e.puntuacion IS NULL) AS puntuacion_nula,
       count(*) FILTER (WHERE e.puntuacion > e.escala_max) AS sobre_escala,
       count(*) FILTER (WHERE e.puntuacion >= 1 AND e.puntuacion <= e.escala_max) AS validas,
       round(avg(e.puntuacion) FILTER (WHERE e.puntuacion >= 1 AND e.puntuacion <= e.escala_max)::numeric, 3) AS media_valida
FROM public.fact_evaluacion_docente e
JOIN public.dim_origen_documental d ON d.id_documento = e.id_documento
JOIN public.dim_tiempo t ON t.id_tiempo = e.id_tiempo
GROUP BY 1,2,3,4,5,6,7
ORDER BY 1,5,6,7;
