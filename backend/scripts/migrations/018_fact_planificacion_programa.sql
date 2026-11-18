-- =============================================================================
-- 018 · PLANIFICACION al DW (Diseño B, V-3)
-- Agrega fact_planificacion_programa y trazabilidad por carga_fila_origen en dim_meta.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.fact_planificacion_programa (
  id_planificacion BIGSERIAL PRIMARY KEY,
  id_modulo INTEGER NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE SET NULL,
  id_tiempo_plan INTEGER NULL REFERENCES public.dim_tiempo(id_tiempo) ON DELETE SET NULL,
  id_documento INTEGER NOT NULL REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
  clave_fila_origen VARCHAR(64) NOT NULL UNIQUE
    REFERENCES public.carga_fila_origen(clave) ON DELETE CASCADE,
  clave_contenido CHAR(64) NOT NULL,
  hoja VARCHAR(200) NOT NULL,
  fila_excel INTEGER NOT NULL,
  pos_code_fuente VARCHAR(80) NULL,
  nombre_programa TEXT NULL,
  tipo_programa VARCHAR(100) NULL,
  escuela VARCHAR(120) NULL,
  origen_programa VARCHAR(120) NULL,
  diseno_curricular VARCHAR(160) NULL,
  fecha_notificacion DATE NULL,
  fecha_inicio_plan DATE NULL,
  fecha_fin_plan DATE NULL,
  duracion_meses NUMERIC(8,2) NULL,
  estado_fuente VARCHAR(120) NULL,
  notificado BOOLEAN NULL,
  costo_programa NUMERIC(14,2) NULL,
  costo_descuento_20 NUMERIC(14,2) NULL,
  tarifa_contado_100 NUMERIC(14,2) NULL,
  tarifa_contado_80 NUMERIC(14,2) NULL,
  punto_equilibrio NUMERIC(14,2) NULL,
  leads_fuente NUMERIC(14,2) NULL,
  reservas_fuente NUMERIC(14,2) NULL,
  inscritos_fuente NUMERIC(14,2) NULL,
  pauta_ejecutada NUMERIC(14,2) NULL,
  pauta_asignada NUMERIC(14,2) NULL,
  payload_fuente JSONB NULL,
  requiere_revision BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_fact_plan_pos_mes
  ON public.fact_planificacion_programa(pos_code_fuente, id_tiempo_plan);
CREATE INDEX IF NOT EXISTS ix_fact_plan_documento
  ON public.fact_planificacion_programa(id_documento);

ALTER TABLE public.dim_meta
  ADD COLUMN IF NOT EXISTS id_documento INTEGER NULL REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS clave_fila_origen VARCHAR(64) NULL,
  ADD COLUMN IF NOT EXISTS celda_origen VARCHAR(120) NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_dim_meta_clave_fila_origen'
  ) THEN
    ALTER TABLE public.dim_meta
      ADD CONSTRAINT uq_dim_meta_clave_fila_origen UNIQUE (clave_fila_origen);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_dim_meta_carga_fila_origen'
  ) THEN
    ALTER TABLE public.dim_meta
      ADD CONSTRAINT fk_dim_meta_carga_fila_origen FOREIGN KEY (clave_fila_origen)
      REFERENCES public.carga_fila_origen(clave) ON DELETE CASCADE;
  END IF;
END $$;

INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('018_fact_planificacion_programa.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

COMMIT;
