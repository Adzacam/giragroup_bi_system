-- Migración 016 (B-9): Trazabilidad individual de descartes e identificador determinista de homónimos (Estado C)
-- No crea tablas nuevas (invariante: 50 tablas + 9 vistas bi).
-- NO aplicar a giragroup_db viva sin aprobación explícita de Lean.

ALTER TABLE log_inconsistencias
    ADD COLUMN IF NOT EXISTS regla_origen VARCHAR(80);

ALTER TABLE stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS id_homonimo VARCHAR(32);

CREATE INDEX IF NOT EXISTS ix_log_inconsistencias_regla_origen
    ON log_inconsistencias (regla_origen);

CREATE INDEX IF NOT EXISTS ix_stg_entidad_id_homonimo
    ON stg_entidad_no_resuelta (id_homonimo);
