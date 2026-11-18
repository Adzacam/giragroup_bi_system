-- =============================================================================
-- 017 · Preparación de revisión (Fase A, W-5) como tipo de tarea en dataops_tarea
-- =============================================================================
BEGIN;

ALTER TABLE public.dataops_tarea DROP CONSTRAINT IF EXISTS dataops_tarea_tipo_check;
ALTER TABLE public.dataops_tarea ADD CONSTRAINT dataops_tarea_tipo_check
    CHECK (tipo IN ('INGESTA', 'LECTURA_BETO', 'PREPARACION_REVISION', 'CONSOLIDACION'));

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('017_dataops_tarea_preparacion_revision.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
