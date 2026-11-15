-- =============================================================================
-- 015 · Caché de las entidades NER que devuelve BETO por texto (opciones 1–3 de la integración de BETO)
--
-- cache_indice_beto guarda un solo número por texto (el índice); las opciones de la cascada final, el acuerdo regla–BETO y la
-- sugerencia en la bandeja necesitan la lista de entidades (tipo, tramo y probabilidad). Se guarda por hash del texto y por
-- configuración del modelo (versión, ventana y solape), de modo que cambiar cualquiera de ellas invalida la entrada.
--
-- NO está en MIGRACIONES_EN_ARRANQUE: con los flags BETO_* apagados nada la usa. services/beto_integracion.py la crea
-- (CREATE TABLE IF NOT EXISTS, el mismo texto) la primera vez que un flag está encendido.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.cache_beto_entidades (
    hash_texto   CHAR(64)     NOT NULL,
    configuracion VARCHAR(80) NOT NULL,
    entidades    TEXT         NOT NULL,
    creado_en    TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hash_texto, configuracion)
);

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('015_cache_beto_entidades.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
