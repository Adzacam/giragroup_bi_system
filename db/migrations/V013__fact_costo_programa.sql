-- ==============================================================================
-- Migración V013: fact_costo_programa
--
-- Egreso, ingreso y rentabilidad por programa (POS). fact_rentabilidad tiene la llave única
-- (id_categoria, id_tiempo): es una serie mensual por categoría y no admite un monto por programa,
-- por eso las filas de costos por POS se descartaban como ruido. Idempotente.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.fact_costo_programa (
    id_hecho_costo SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL UNIQUE REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    egreso_anterior NUMERIC(14, 2),
    egreso_real NUMERIC(14, 2),
    ingreso NUMERIC(14, 2),
    rentabilidad NUMERIC(14, 2),
    requiere_revision BOOLEAN DEFAULT FALSE,
    motivo_revision VARCHAR(300),
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
