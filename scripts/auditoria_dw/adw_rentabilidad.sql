-- ADW L0 · bloque rentabilidad (A4, C5): meta y ejecución por gestión y mes
SELECT t.gestion, t.mes,
       count(*) AS filas,
       round(sum(r.monto_ejecutado)::numeric, 2) AS ejecutado_bs,
       round(sum(r.monto_meta)::numeric, 2) AS meta_bs
FROM public.fact_rentabilidad r
JOIN public.dim_tiempo t ON t.id_tiempo = r.id_tiempo
GROUP BY 1,2
ORDER BY 1,2;
