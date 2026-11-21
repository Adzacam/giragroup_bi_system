-- =============================================================================
-- 023 · FU-L3 Inscritos: cada fila de fact_marketing sabe de qué documento viene
-- =============================================================================
-- Causa raíz del ×2 de inscritos (hallazgo FU-L3): borrar un documento quitaba sus hechos de todas las tablas
-- que tienen id_documento y la huella de idempotencia (carga_fila_origen), pero fact_marketing no tenía id_documento:
-- sus inscripciones se quedaban. Volver a subir el mismo libro volvía a sumarlas (7.102 frente a 3.551 en 2023).
-- Cambio mínimo y no destructivo: una columna nueva (nullable) con FK a dim_origen_documental ON DELETE CASCADE, su
-- índice y la restricción única (programa, día) ampliada con el documento (más permisiva: ningún dato existente la viola). Ninguna tabla ni vista nueva (siguen 51 tablas + 10 vistas bi). Idempotente: se puede aplicar dos veces.
-- Las filas que ya existen quedan con id_documento NULL (de origen desconocido): NO se tocan. Si la DW ya tiene
-- inscripciones duplicadas, se corrigen vaciando fact_marketing y volviendo a cargar la tabla de inscripciones
-- (decisión de Lean / FU-L9): desde esta migración el borrado de un documento retira sus filas.
-- Las filas de captación (leads_captacion / inscritos_captacion, KPI-06) vienen de planificación, que sí tiene
-- id_documento; se guardan con id_documento NULL porque son una sola cifra por programa y mes entre varios documentos.
BEGIN;

ALTER TABLE public.fact_marketing
    ADD COLUMN IF NOT EXISTS id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_fact_marketing_documento ON public.fact_marketing (id_documento);

-- El grano pasa de (programa, día) a (programa, día, documento): dos documentos pueden traer inscripciones del mismo
-- programa y día, y la captación de planificación (id_documento NULL) convive con ellas. Se reemplaza la restricción
-- única por un índice único equivalente que incluye el documento (NULL cuenta como 0, así las filas sin documento
-- siguen siendo únicas por programa y día).
ALTER TABLE public.fact_marketing DROP CONSTRAINT IF EXISTS uq_fact_marketing_modulo_tiempo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_marketing_modulo_tiempo_documento
    ON public.fact_marketing (id_modulo, id_tiempo, COALESCE(id_documento, 0));
COMMENT ON COLUMN public.fact_marketing.id_documento IS
    'FU-L3: documento de origen de las inscripciones de la fila (NULL: captación de planificación o filas anteriores a la 023). Borrar el documento borra la fila.';

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('023_fu_l3_fact_marketing_documento.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
