-- =============================================================================
-- MIGRACIÓN V004: TABLAS DE METAS Y PRONÓSTICOS (FORECASTING)
-- ÉPICA: GIRA-23 | TICKET: GIRA-52
-- =============================================================================

-- 1. DIMENSIÓN DE METAS PRESUPUESTARIAS Y OPERATIVAS
CREATE TABLE IF NOT EXISTS public.dim_meta (
    id_meta         SERIAL PRIMARY KEY,
    categoria       VARCHAR(50) NOT NULL, -- 'PROGRAMAS', 'TECHOS_CERRADOS', 'FINANCIERO_ANUAL'
    id_tiempo       INT REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    monto_meta      NUMERIC(14,2),
    tipo_programa   VARCHAR(50)           -- NULL si meta global; o 'DIPLOMADO', 'CURSO', 'PROGRAMA EXPERTO'
);

CREATE INDEX IF NOT EXISTS idx_dim_meta_tiempo ON public.dim_meta(id_tiempo);
CREATE INDEX IF NOT EXISTS idx_dim_meta_cat ON public.dim_meta(categoria);

-- 2. TABLA DE HECHOS: RESULTADOS DE FORECASTING
CREATE TABLE IF NOT EXISTS public.fact_forecast (
    id_forecast     SERIAL PRIMARY KEY,
    caso_uso        VARCHAR(50) NOT NULL, 
    -- 'ALUMNOS_GLOBAL', 'ALUMNOS_DIPLOMADO', 'ALUMNOS_CURSO', 'ALUMNOS_EXPERTO', 'META_MENSUAL_PROGRAMAS', 'META_ANUAL'
    id_tiempo       INT REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    valor_forecast  NUMERIC(14,2) NOT NULL,
    ic_lower        NUMERIC(14,2),        -- Intervalo inferior (NULL para estimaciones puntuales/OLS N=3)
    ic_upper        NUMERIC(14,2),        -- Intervalo superior (NULL para estimaciones puntuales/OLS N=3)
    metodo          VARCHAR(30) NOT NULL DEFAULT 'HoltWinters', -- 'HoltWinters', 'OLS'
    horizonte_meses INT NOT NULL,         -- Desplazamiento en periodos (1 a 6 meses)
    generado_en     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_forecast_caso_tiempo UNIQUE (caso_uso, id_tiempo)
);

CREATE INDEX IF NOT EXISTS idx_fact_forecast_caso ON public.fact_forecast(caso_uso);
