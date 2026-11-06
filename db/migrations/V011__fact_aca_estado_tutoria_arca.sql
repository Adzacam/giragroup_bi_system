-- ==============================================================================
-- Migración V011: estados del acta ARCA en fact_rendimiento_academico
--
-- El estado académico se toma de la fuente (Participó, Deserción, En curso…) en vez de
-- deducirse de la nota, y se guardan los otros dos ejes de la hoja CRITERIOS para validar
-- la combinación (académico, tutoría/reprobado, ARCA). Idempotente.
-- ==============================================================================

ALTER TABLE public.fact_rendimiento_academico ADD COLUMN IF NOT EXISTS estado_tutoria VARCHAR(50);
ALTER TABLE public.fact_rendimiento_academico ADD COLUMN IF NOT EXISTS estado_arca VARCHAR(50);
