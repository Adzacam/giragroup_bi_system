-- =============================================================================
-- MIGRACIÓN V006: TABLA DE STAGING PARA ENTIDADES NLP NO RESUELTAS (FK ESTADO C)
-- =============================================================================
-- Almacena entidades detectadas por BETO NER cuya resolución contra catálogos
-- dimensionales no fue posible automáticamente (score fuzzy < umbral o sin
-- candidato). Permite revisión humana diferida por AUDITOR_CALIDAD.

CREATE TABLE IF NOT EXISTS public.stg_entidad_no_resuelta (
    id_staging              SERIAL PRIMARY KEY,
    id_documento            INT REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
    tipo_entidad            VARCHAR(30) NOT NULL,
    texto_original          TEXT NOT NULL,
    ci_temporal             VARCHAR(30),
    mejor_candidato         TEXT,
    score_fuzzy             NUMERIC(5,2),
    fk_estado               VARCHAR(1) DEFAULT 'C',
    nivel_confianza         NUMERIC(5,4),
    resuelto                BOOLEAN DEFAULT FALSE,
    resuelto_por            INT REFERENCES public.users(id) ON DELETE SET NULL,
    resuelto_en             TIMESTAMP,
    id_dimension_resuelta   INT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_estado
ON public.stg_entidad_no_resuelta(resuelto);

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_tipo
ON public.stg_entidad_no_resuelta(tipo_entidad);

CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_doc
ON public.stg_entidad_no_resuelta(id_documento);

-- RLS: misma política del esquema constelación
ALTER TABLE public.stg_entidad_no_resuelta ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Lectura_Global" ON public.stg_entidad_no_resuelta
    FOR SELECT USING (true);

CREATE POLICY "Admin_All_Access" ON public.stg_entidad_no_resuelta
    FOR ALL USING (
        (current_setting('request.jwt.claims', true)::json->>'role') = 'admin'
    );
