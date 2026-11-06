-- =============================================================================
-- 008 · Progreso de tareas largas de DataOps (lectura de BETO y consolidación al DW)
--
-- Con archivos reales (100 mil registros) la consolidación tarda más que cualquier timeout HTTP y la lectura
-- de BETO varios minutos. Cada tarea registra su avance aquí para que la SPA muestre progreso, tiempo
-- transcurrido y estimado. Vive en la base (no en memoria) porque la API corre con varios workers.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.dataops_tarea (
    id              SERIAL PRIMARY KEY,
    tipo            VARCHAR(20)  NOT NULL CHECK (tipo IN ('CONSOLIDACION', 'LECTURA_BETO')),
    id_lote         INTEGER,
    estado          VARCHAR(15)  NOT NULL DEFAULT 'EN_CURSO'
                    CHECK (estado IN ('EN_CURSO', 'COMPLETADA', 'ERROR')),
    total           INTEGER      NOT NULL DEFAULT 0,
    procesados      INTEGER      NOT NULL DEFAULT 0,
    resultado       JSONB,
    error           TEXT,
    iniciado_por    VARCHAR(100),
    iniciado_en     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    terminado_en    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_dataops_tarea_lote ON public.dataops_tarea (id_lote, tipo, id DESC);

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('008_dataops_tarea.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
