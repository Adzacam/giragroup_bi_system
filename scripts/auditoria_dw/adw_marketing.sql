-- ADW L0 · bloque marketing (A5): leads, reservas e inscritos por gestión
SELECT t.gestion, count(*) AS filas,
       sum(m.leads) AS leads, sum(m.reservas) AS reservas, sum(m.inscritos) AS inscritos,
       count(m.leads_captacion) AS filas_leads_captacion, count(m.inscritos_captacion) AS filas_inscritos_captacion
FROM public.fact_marketing m
JOIN public.dim_tiempo t ON t.id_tiempo = m.id_tiempo
GROUP BY 1
ORDER BY 1;
