-- ==============================================================================
-- Migración V012: fact_evaluacion_docente con una fila por respuesta
--
-- tipo_pregunta separa lo que evalúa al docente de la satisfacción institucional y el NPS;
-- escala_max permite promediar Likert 1-5 y NPS 0-10 sin mezclarlos; clave_respuesta hace
-- idempotente la carga (subir el mismo archivo otra vez actualiza en vez de duplicar).
-- Las filas cargadas antes de esta versión tienen puntuacion 5.0 de relleno y clave NULL:
-- deben recargarse desde el archivo fuente. Idempotente.
-- ==============================================================================

ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS tipo_pregunta VARCHAR(20);
ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS escala_max INTEGER;
ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS clave_respuesta VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_eval_clave ON public.fact_evaluacion_docente (clave_respuesta);
