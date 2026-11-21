-- FU-L2 · Prepara la copia tmpfs para recargar la cobranza. SOLO la copia tmpfs (127.0.0.1:554xx); nunca la DW viva
-- ni el snapshot. Uso desde el host:
--   psql "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55437/giragroup_db" -v ON_ERROR_STOP=1 \
--        -f backend/scripts/migrations/022_fu_l2_cobranza_mora_da3.sql -f scripts/auditoria_fuentes/fu_l2_preparar_tmpfs.sql
-- 1) la migración 022 (idempotente) deja las dos columnas nuevas y las tres vistas con DA3;
-- 2) este archivo borra lo cargado antes de cobranza para que la recarga no se salte filas por idempotencia
--    (carga_fila_origen reclama cada fila) y deja el libro como «no cargado» para el control de duplicados por hash.
BEGIN;
DELETE FROM public.fact_situacion_financiera;
DELETE FROM public.carga_fila_origen WHERE tabla = 'fact_situacion_financiera';
UPDATE public.dim_origen_documental SET hash_sha256 = NULL WHERE tipo_fuente = 'COBRANZA';
COMMIT;
