-- ==============================================================================
-- Migración V010: índices en las FK de los hechos que no los tenían (RNF-03)
--
-- fact_rendimiento_academico y fact_situacion_financiera ya indexan id_tiempo,
-- id_estudiante e id_modulo. Faltaban las FK de marketing, rentabilidad, cobranzas
-- proyectadas, evaluación docente y dim_meta, y dim_tiempo(gestion), que filtra todos
-- los KPI del CMI por gestión. Idempotente.
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_fact_mkt_tiempo        ON public.fact_marketing (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_rent_tiempo       ON public.fact_rentabilidad (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_cobproy_tiempo    ON public.fact_cobranzas_proyectadas (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_estudiante   ON public.fact_evaluacion_docente (id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_eval_modulo       ON public.fact_evaluacion_docente (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_tiempo       ON public.fact_evaluacion_docente (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_docente      ON public.fact_evaluacion_docente (id_docente);
CREATE INDEX IF NOT EXISTS idx_dim_meta_tiempo        ON public.dim_meta (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_dim_tiempo_gestion     ON public.dim_tiempo (gestion);
-- Regla financiera de alertas tempranas (cuotas_impagas >= 2)
CREATE INDEX IF NOT EXISTS idx_fact_fin_mora_estudiante
    ON public.fact_situacion_financiera (id_estudiante) WHERE cuotas_impagas >= 2;

ANALYZE public.fact_situacion_financiera, public.fact_rendimiento_academico, public.fact_marketing,
        public.fact_rentabilidad, public.dim_tiempo, public.dim_modulo, public.dim_meta;
