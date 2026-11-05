-- =============================================================================
-- 009 · Caché del índice de confianza de BETO por línea
--
-- La inferencia de BETO es ~2/3 del tiempo de consolidación (CPU: ~20 ms por línea). El índice de una línea
-- sólo depende de su texto y del modelo: se guarda por hash para que reconsolidar, reprocesar o subir de
-- nuevo el mismo archivo no vuelva a inferir. Cambiar de modelo (BETO_MODELO_VERSION) invalida la caché.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.cache_indice_beto (
    hash_texto  CHAR(64)     NOT NULL,
    modelo      VARCHAR(40)  NOT NULL,
    indice      NUMERIC(6,4) NOT NULL,
    creado_en   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hash_texto, modelo)
);

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('009_cache_indice_beto.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
