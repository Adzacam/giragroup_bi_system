-- FU-L5 · Prepara la copia tmpfs para recargar las encuestas. SOLO la copia tmpfs (127.0.0.1:554xx); nunca la DW viva ni el
-- snapshot. Uso desde el host (las migraciones 014, 016 a 025 se aplican antes):
--   psql "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55440/giragroup_db" -v ON_ERROR_STOP=1 -f scripts/auditoria_fuentes/fu_l5_preparar_tmpfs.sql
-- Borra los hechos de evaluación docente previos y sus claves de idempotencia (carga_fila_origen reclama cada fila) y deja los
-- libros ya cargados como «no cargados» para el control de duplicados por hash (un libro de encuestas pudo haber quedado
-- tipificado como acta). Los avisos de calidad de esos documentos se conservan como historia; el caché de BETO no se toca.
BEGIN;
DELETE FROM public.fact_evaluacion_docente;
DELETE FROM public.carga_fila_origen WHERE tabla = 'fact_evaluacion_docente';
UPDATE public.dim_origen_documental SET hash_sha256 = NULL WHERE tipo_fuente IN ('EVALUACION_DOCENTE', 'ACTA');
COMMIT;
