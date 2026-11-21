-- ADW L0 · bloque cartera (A3): estado_cartera de la fuente frente a cuotas_impagas, por gestión
SELECT t.gestion, f.estado_cartera,
       count(*) AS filas, count(DISTINCT f.id_estudiante) AS estudiantes,
       count(*) FILTER (WHERE f.cuotas_impagas = 0) AS cuotas_0,
       count(*) FILTER (WHERE f.cuotas_impagas = 1) AS cuotas_1,
       count(*) FILTER (WHERE f.cuotas_impagas >= 2) AS cuotas_2_mas,
       round(sum(f.monto_deuda)::numeric, 2) AS deuda_bs
FROM public.fact_situacion_financiera f
JOIN public.dim_tiempo t ON t.id_tiempo = f.id_tiempo
GROUP BY 1,2
ORDER BY 1,2;
