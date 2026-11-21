-- 020_retirar_rol_powerbi_reader.sql
-- Decisión D2 (REESTRUCTURACION_VISTA_V2): retirar el rol powerbi_reader de forma idempotente.
-- La migración 006 permanece intacta en el historial; en instalaciones limpias 006 lo crea y 020 lo retira.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'powerbi_reader') THEN
        BEGIN
            ALTER DEFAULT PRIVILEGES IN SCHEMA bi REVOKE SELECT ON TABLES FROM powerbi_reader;
            REVOKE ALL ON ALL TABLES IN SCHEMA bi FROM powerbi_reader;
            REVOKE USAGE ON SCHEMA bi FROM powerbi_reader;
            DROP OWNED BY powerbi_reader;
            DROP ROLE powerbi_reader;
        EXCEPTION
            WHEN insufficient_privilege OR dependent_objects_still_exist THEN
                RAISE NOTICE 'No se pudo eliminar powerbi_reader (privilegios o dependencias en otras bases del clúster); permisos revocados en esta base.';
        END;
    END IF;
END
$$;

INSERT INTO public.schema_migrations (version)
VALUES ('020_retirar_rol_powerbi_reader.sql')
ON CONFLICT (version) DO NOTHING;
