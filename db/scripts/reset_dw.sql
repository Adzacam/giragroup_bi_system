-- ============================================================================
-- db/scripts/reset_dw.sql
-- Propósito: Reset Limpio y Seguro del Data Warehouse y Staging
-- 
-- Reglas Críticas:
-- 1. TRUNCATE en cascada de todas las tablas de hechos (fact_*).
-- 2. TRUNCATE en cascada de todas las tablas de staging, gobernanza y logs.
-- 3. PRESERVACIÓN ESTRICTA de:
--    - users (credenciales de autenticación)
--    - cat_institucion (y catálogos maestros 3NF)
--    - dim_tiempo (calendario dimensional)
-- ============================================================================

BEGIN;

TRUNCATE TABLE
    public.fact_rendimiento_academico,
    public.fact_situacion_financiera,
    public.fact_evaluacion_docente,
    public.fact_marketing,
    public.fact_rentabilidad,
    public.fact_forecast,
    public.fact_cobranzas_proyectadas,
    public.stg_entidad_no_resuelta,
    public.staging_registros_crudos,
    public.log_pipeline_ingesta,
    public.log_inconsistencias,
    public.log_auditoria_nlp,
    public.dim_origen_documental,
    public.lote
RESTART IDENTITY CASCADE;

COMMIT;

-- Verificación de estado final:
DO $$
DECLARE
    r RECORD;
    cnt INT;
BEGIN
    RAISE NOTICE '=== Verificación Post-Reset ===';
    FOR r IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (tablename LIKE 'fact_%' OR tablename IN ('stg_entidad_no_resuelta', 'staging_registros_crudos', 'log_pipeline_ingesta', 'dim_origen_documental', 'lote'))
    LOOP
        EXECUTE format('SELECT count(*) FROM public.%I', r.tablename) INTO cnt;
        IF cnt > 0 THEN
            RAISE EXCEPTION 'Tabla % no quedó vacía (filas: %)', r.tablename, cnt;
        ELSE
            RAISE NOTICE 'Tabla %: 0 filas [OK]', r.tablename;
        END IF;
    END LOOP;

    -- Verificar preservación
    EXECUTE 'SELECT count(*) FROM public.users' INTO cnt;
    RAISE NOTICE 'Preservada tabla users: % filas', cnt;

    EXECUTE 'SELECT count(*) FROM public.dim_tiempo' INTO cnt;
    RAISE NOTICE 'Preservada tabla dim_tiempo: % filas', cnt;

    EXECUTE 'SELECT count(*) FROM public.cat_institucion' INTO cnt;
    RAISE NOTICE 'Preservada tabla cat_institucion: % filas', cnt;
END $$;
