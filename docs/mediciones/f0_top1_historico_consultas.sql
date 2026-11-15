BEGIN TRANSACTION READ ONLY;
SELECT json_build_object('source','beto_pg_tmpfs/giragroup_db historical isolated copy','table','log_auditoria_nlp','rows',COUNT(*),'with_auditor',COUNT(usuario_auditor),'with_correction',COUNT(correccion_humana),'with_prediction',COUNT(prediccion_beto),'earliest',MIN(created_at),'latest',MAX(created_at)) FROM public.log_auditoria_nlp;
SELECT json_build_object('columns',json_agg(column_name ORDER BY ordinal_position)) FROM information_schema.columns WHERE table_schema='public' AND table_name='log_auditoria_nlp';
SELECT json_build_object('resolved_staging_rows',COUNT(*),'with_actor',COUNT(resuelto_por),'with_decision_timestamp',COUNT(resuelto_en)) FROM public.stg_entidad_no_resuelta WHERE resuelto IS TRUE;
ROLLBACK;
