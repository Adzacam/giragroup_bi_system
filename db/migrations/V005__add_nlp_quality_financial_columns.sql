-- =============================================================================
-- MIGRACIÓN V005: COLUMNAS DE CALIDAD NLP, ESTADO FK Y TRAZABILIDAD FINANCIERA
-- =============================================================================

-- 1. ACTUALIZAR TABLA: fact_rendimiento_academico
-- Añadir estado de resolución FK (A: CI directo, B: difuso padrón, C: sintético temporal)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'fact_rendimiento_academico' 
          AND column_name = 'fk_estado'
    ) THEN
        ALTER TABLE public.fact_rendimiento_academico 
        ADD COLUMN fk_estado VARCHAR(1) DEFAULT 'A';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_fact_rendimiento_fk_estado 
ON public.fact_rendimiento_academico(fk_estado);

-- 2. ACTUALIZAR TABLA: fact_situacion_financiera
-- Añadir trazabilidad documental, confianza probabilística NLP, flag de revisión y estado FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'fact_situacion_financiera' 
          AND column_name = 'id_documento'
    ) THEN
        ALTER TABLE public.fact_situacion_financiera 
        ADD COLUMN id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'fact_situacion_financiera' 
          AND column_name = 'nivel_confianza_ia'
    ) THEN
        ALTER TABLE public.fact_situacion_financiera 
        ADD COLUMN nivel_confianza_ia NUMERIC(5, 4);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'fact_situacion_financiera' 
          AND column_name = 'requiere_revision'
    ) THEN
        ALTER TABLE public.fact_situacion_financiera 
        ADD COLUMN requiere_revision BOOLEAN DEFAULT FALSE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'fact_situacion_financiera' 
          AND column_name = 'fk_estado'
    ) THEN
        ALTER TABLE public.fact_situacion_financiera 
        ADD COLUMN fk_estado VARCHAR(1) DEFAULT 'A';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_fact_financiera_fk_estado 
ON public.fact_situacion_financiera(fk_estado);

CREATE INDEX IF NOT EXISTS idx_fact_financiera_revision 
ON public.fact_situacion_financiera(requiere_revision);
