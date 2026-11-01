-- =============================================================================
-- MIGRACIÓN V007: EXTENSIÓN DE STAGING PARA ENTIDADES NO RESUELTAS (HITL)
-- =============================================================================
-- Agrega columnas para explicabilidad de motivo, payload semántico estructurado,
-- trazabilidad de fila origen, estados de resolución con commit diferido,
-- y bloqueo pesimista con tiempo de expiración (lease/TTL).

ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS motivo VARCHAR(100),
    ADD COLUMN IF NOT EXISTS payload_json TEXT,
    ADD COLUMN IF NOT EXISTS registro_origen_id INT,
    ADD COLUMN IF NOT EXISTS estado_resolucion VARCHAR(30) DEFAULT 'PENDIENTE',
    ADD COLUMN IF NOT EXISTS lock_usuario_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS lock_expira TIMESTAMP,
    ADD COLUMN IF NOT EXISTS version INT DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_motivo
ON public.stg_entidad_no_resuelta(motivo);

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_estado_res
ON public.stg_entidad_no_resuelta(estado_resolucion);

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_lock
ON public.stg_entidad_no_resuelta(lock_usuario_id, lock_expira);
