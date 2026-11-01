-- ============================================================================
-- Migración Versionada: 005_alinear_esquema_con_ddl.sql
-- Propósito:
--   Alinear una base creada por versiones anteriores con el DDL del repositorio (db/schema.sql).
--   1. uq_fact_aca_est_mod repite la restricción uq_fact_rendimiento_estudiante_modulo.
-- Idempotente: se puede volver a aplicar sobre una base ya alineada.
-- ============================================================================

BEGIN;

DROP INDEX IF EXISTS public.uq_fact_aca_est_mod;

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('005_alinear_esquema_con_ddl.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

COMMIT;
