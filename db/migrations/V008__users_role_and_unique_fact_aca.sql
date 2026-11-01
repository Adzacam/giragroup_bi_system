-- ==============================================================================
-- Migración V008: Refuerzo de Integridad en Users y fact_rendimiento_academico
-- 1. Quitar DEFAULTs de users y exigir role NOT NULL con restricción de dominio CHECK
-- 2. Índice único (id_estudiante, id_modulo) para evitar duplicación de hechos
-- ==============================================================================

-- 1. Normalización y actualización de tabla users
UPDATE public.users SET role = UPPER(role) WHERE role IS NOT NULL;

ALTER TABLE public.users ALTER COLUMN username DROP DEFAULT;
ALTER TABLE public.users ALTER COLUMN hashed_password DROP DEFAULT;
ALTER TABLE public.users ALTER COLUMN email DROP DEFAULT;
ALTER TABLE public.users ALTER COLUMN role DROP DEFAULT;

ALTER TABLE public.users ALTER COLUMN role SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role' AND conrelid = 'public.users'::regclass
    ) THEN
        ALTER TABLE public.users 
        ADD CONSTRAINT ck_users_role 
        CHECK (role IN ('ADMIN','AUDITOR_CALIDAD','DIRECTOR_ACADEMICO','ANALISTA_FINANCIERO','ANALISTA_MARKETING'));
    END IF;
END $$;

-- 2. Índice único en fact_rendimiento_academico
CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_aca_est_mod ON public.fact_rendimiento_academico(id_estudiante, id_modulo);
