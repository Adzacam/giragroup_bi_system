-- FU-L4 · Prepara la copia tmpfs para recargar las actas. SOLO la copia tmpfs (127.0.0.1:554xx); nunca la DW viva ni el
-- snapshot. Uso desde el host (la migración 024 se aplica antes, junto con la 014 y la 016 a la 023):
--   psql "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55439/giragroup_db" -v ON_ERROR_STOP=1 --        -f backend/scripts/migrations/024_fu_l4_actas_resultado_desercion.sql -f scripts/auditoria_fuentes/fu_l4_preparar_tmpfs.sql
-- Borra los hechos académicos previos y sus claves de idempotencia (carga_fila_origen reclama cada fila) y deja los libros
-- de tipo ACTA como «no cargados» para el control de duplicados por hash.
BEGIN;
DELETE FROM public.fact_rendimiento_academico;
DELETE FROM public.carga_fila_origen WHERE tabla = 'fact_rendimiento_academico';
UPDATE public.dim_origen_documental SET hash_sha256 = NULL WHERE tipo_fuente = 'ACTA';
COMMIT;
