-- FU-L9 · Limpieza controlada de hechos, staging e idempotencia en giragroup_db
-- previo a la recarga completa de los 10 libros fuente con las reglas FU-L1..FU-L9.
-- Requiere backup preventivo previo en backups/.
BEGIN;
DELETE FROM public.fact_rendimiento_academico;
DELETE FROM public.fact_situacion_financiera;
DELETE FROM public.fact_evaluacion_docente;
DELETE FROM public.fact_marketing;
DELETE FROM public.fact_rentabilidad;
DELETE FROM public.fact_techo_convenio;
DELETE FROM public.fact_planificacion_programa;
DELETE FROM public.fact_costo_programa;
DELETE FROM public.dim_meta;
DELETE FROM public.carga_fila_origen;
DELETE FROM public.stg_entidad_no_resuelta;
DELETE FROM public.staging_registros_crudos;
DELETE FROM public.log_inconsistencias;
UPDATE public.dim_origen_documental SET hash_sha256 = NULL;
COMMIT;
