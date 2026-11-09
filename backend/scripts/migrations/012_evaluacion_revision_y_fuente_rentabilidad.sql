BEGIN;

-- 012: evaluación docente entra a la bandeja HITL (docente sin vincular o sin fecha) y la recaudación mensual
-- guarda de qué documento viene la cifra vigente (precedencia de fuentes: EJECUTADO VS META sobre BD Egresos).
ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL;
ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS requiere_revision BOOLEAN DEFAULT FALSE;
ALTER TABLE public.fact_evaluacion_docente ADD COLUMN IF NOT EXISTS motivo_revision VARCHAR(300);
CREATE INDEX IF NOT EXISTS idx_fact_eval_revision ON public.fact_evaluacion_docente (id_documento, id_modulo) WHERE requiere_revision;
ALTER TABLE public.fact_rentabilidad ADD COLUMN IF NOT EXISTS id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('012_evaluacion_revision_y_fuente_rentabilidad.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
