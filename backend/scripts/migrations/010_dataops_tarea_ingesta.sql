-- =============================================================================
-- 010 · La ingesta de un lote también registra su avance en dataops_tarea
-- =============================================================================
BEGIN;

ALTER TABLE public.dataops_tarea DROP CONSTRAINT IF EXISTS dataops_tarea_tipo_check;
ALTER TABLE public.dataops_tarea ADD CONSTRAINT dataops_tarea_tipo_check
    CHECK (tipo IN ('INGESTA', 'LECTURA_BETO', 'CONSOLIDACION'));

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('010_dataops_tarea_ingesta.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
