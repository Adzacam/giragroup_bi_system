-- =============================================================================
-- 007 · Versiones del informe de Power BI Desktop (giragroup_cmi.pbix)
--
-- Power BI se usa en Desktop (sin Power BI Service ni licencia Pro). El ADMIN descarga el
-- .pbix desde el CMI, lo edita y sube una nueva versión; los roles con acceso de lectura
-- descargan siempre la versión vigente. El archivo vive en uploads/powerbi/ y aquí sólo su
-- metadato. Idempotente.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.powerbi_informe_version (
    id              SERIAL PRIMARY KEY,
    version         INTEGER      NOT NULL UNIQUE,
    nombre_archivo  VARCHAR(255) NOT NULL,
    ruta            VARCHAR(500) NOT NULL,
    tamano_bytes    BIGINT       NOT NULL CHECK (tamano_bytes > 0),
    sha256          CHAR(64)     NOT NULL,
    nota            VARCHAR(300),
    vigente         BOOLEAN      NOT NULL DEFAULT FALSE,
    subido_por      VARCHAR(100) NOT NULL,
    subido_en       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Una sola versión vigente
CREATE UNIQUE INDEX IF NOT EXISTS ux_powerbi_informe_vigente
    ON public.powerbi_informe_version (vigente) WHERE vigente;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('007_powerbi_informe_version.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
