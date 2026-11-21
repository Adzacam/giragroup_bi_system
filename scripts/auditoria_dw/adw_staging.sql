-- ADW L0 · bloque staging (pregunta 3): pendientes y descartes por tipo, motivo y documento
SELECT s.tipo_entidad, s.motivo, s.estado_resolucion, s.resuelto, s.id_documento,
       count(*) AS n,
       round(avg(s.score_fuzzy)::numeric, 1) AS fuzzy_medio,
       round(avg(s.nivel_confianza)::numeric, 3) AS confianza_media
FROM public.stg_entidad_no_resuelta s
GROUP BY 1,2,3,4,5
ORDER BY n DESC;
