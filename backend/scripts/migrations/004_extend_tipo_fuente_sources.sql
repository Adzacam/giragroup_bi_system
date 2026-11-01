-- ============================================================================
-- Migración Versionada: 004_extend_tipo_fuente_sources.sql
-- Propósito:
--   Permitir nuevos orígenes documentales agnósticos en dim_origen_documental:
--   EVALUACION_DOCENTE, EGRESOS, TECHOS, PLANIFICACION, MARKETING, RENTABILIDAD, etc.
-- ============================================================================

BEGIN;

ALTER TABLE public.dim_origen_documental
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_fuente;

ALTER TABLE public.dim_origen_documental
    ADD CONSTRAINT chk_dim_origen_tipo_fuente
    CHECK (tipo_fuente IS NULL OR tipo_fuente IN (
        'ACTA', 'COBRANZA', 'ADMISION', 'MOODLE',
        'EVALUACION_DOCENTE', 'EGRESOS', 'TECHOS', 'PLANIFICACION',
        'MARKETING', 'RENTABILIDAD', 'ERROR', 'RECHAZADO', 'DUPLICADO', 'SIN_RECONOCER'
    ));

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('004_extend_tipo_fuente_sources.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

COMMIT;
