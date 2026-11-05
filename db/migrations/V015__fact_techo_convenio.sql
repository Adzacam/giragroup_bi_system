-- ==============================================================================
-- Migración V015: fact_techo_convenio
--
-- Convenios con instituciones cliente (BD Techos y equivalentes): monto, inscritos y fechas por
-- programa e institución canónica. Antes estas filas se descartaban como ruido. Idempotente.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.fact_techo_convenio (
    id_hecho_techo SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE SET NULL,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    clave_convenio VARCHAR(40) NOT NULL UNIQUE,
    institucion VARCHAR(200) NOT NULL,
    id_convenio_catalogo INTEGER,
    monto_convenio NUMERIC(14, 2),
    n_inscritos INTEGER,
    gestion INTEGER,
    fecha_inicio DATE,
    fecha_fin DATE,
    requiere_revision BOOLEAN DEFAULT FALSE,
    motivo_revision VARCHAR(300),
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fact_techo_modulo ON public.fact_techo_convenio (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_techo_institucion ON public.fact_techo_convenio (institucion);
