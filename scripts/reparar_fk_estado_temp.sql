-- Ronda 8, tarea 2: los miembros nuevos TEMP-hash (sin CI exacta) quedaron como 'A' en cargas anteriores; la semántica unificada los marca 'B'.
UPDATE public.dim_estudiante SET fk_estado = 'B' WHERE id_temporal LIKE 'TEMP-%' AND fk_estado = 'A' AND (ci IS NULL OR ci = '');
