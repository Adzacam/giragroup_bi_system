-- ==============================================================================
-- Migración 001: Optimización de Índices y Eliminación de Índices Redundantes
-- GiraGroup BI System - Aplicación Idempotente en Vivo sobre giragroup_db
-- ==============================================================================

-- 1. Eliminación de índices redundantes creados explícitamente sobre columnas PRIMARY KEY
DROP INDEX IF EXISTS idx_dim_est_id;
DROP INDEX IF EXISTS idx_log_auditoria_nlp_id;
DROP INDEX IF EXISTS idx_fact_rendimiento_aca_id;
DROP INDEX IF EXISTS idx_fact_cobro_id;

-- 2. Creación de índices sobre claves foráneas y columnas de filtro frecuente (Evita Full Table Scans)
CREATE INDEX IF NOT EXISTS idx_fact_rend_estudiante ON fact_rendimiento_academico(id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_rend_modulo ON fact_rendimiento_academico(id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_rend_docente ON fact_rendimiento_academico(id_docente);
CREATE INDEX IF NOT EXISTS idx_fact_rend_tiempo ON fact_rendimiento_academico(id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_rend_documento ON fact_rendimiento_academico(id_documento);

CREATE INDEX IF NOT EXISTS idx_fact_fin_estudiante ON fact_situacion_financiera(id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_fin_modulo ON fact_situacion_financiera(id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_fin_tiempo ON fact_situacion_financiera(id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_fin_documento ON fact_situacion_financiera(id_documento);
CREATE INDEX IF NOT EXISTS idx_fact_fin_estado_cartera ON fact_situacion_financiera(estado_cartera);

CREATE INDEX IF NOT EXISTS idx_stg_entidad_resuelto ON stg_entidad_no_resuelta(resuelto, estado_resolucion);
CREATE INDEX IF NOT EXISTS idx_stg_entidad_registro ON stg_entidad_no_resuelta(registro_origen_id);
CREATE INDEX IF NOT EXISTS idx_stg_entidad_doc ON stg_entidad_no_resuelta(id_documento);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
