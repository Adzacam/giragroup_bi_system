-- FU-L6 · Prepara la copia tmpfs para recargar las metas. SOLO la copia tmpfs (127.0.0.1:554xx); nunca la DW viva ni el snapshot.
-- Uso desde el host (las migraciones 014, 016 a 026 se aplican antes):
--   psql "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55441/giragroup_db" -v ON_ERROR_STOP=1 -f scripts/auditoria_fuentes/fu_l6_preparar_tmpfs.sql
-- Borra las metas y el ejecutado por categoría y mes (fact_rentabilidad, dim_meta), sus claves de idempotencia (carga_fila_origen reclama
-- cada fila), los avisos de conflicto de fuentes anteriores y deja los libros de metas ya cargados como «no cargados» para el control de
-- duplicados por hash. Los costos por programa, los hechos de planificación y sus claves NO se tocan: la recarga los reconoce como ya cargados.
BEGIN;
DELETE FROM public.fact_rentabilidad;
DELETE FROM public.dim_meta;
DELETE FROM public.carga_fila_origen WHERE tabla IN ('fact_rentabilidad', 'dim_meta');
DELETE FROM public.log_inconsistencias WHERE tipo_regla = 'CONFLICTO_FUENTES';
UPDATE public.dim_origen_documental SET hash_sha256 = NULL WHERE tipo_fuente IN ('RENTABILIDAD', 'EGRESOS', 'PLANIFICACION');
COMMIT;
