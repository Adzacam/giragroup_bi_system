-- ADW L0 · bloque tareas DataOps (C1, D3): tareas, estado y duración
SELECT id, tipo, id_lote, estado, total, procesados, iniciado_en, terminado_en,
       round(extract(epoch FROM (coalesce(terminado_en, actualizado_en) - iniciado_en))::numeric, 1) AS segundos,
       left(coalesce(error, ''), 120) AS error
FROM public.dataops_tarea
ORDER BY id;
