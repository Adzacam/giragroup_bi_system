-- ============================================================================
-- Migración Versionada: 003_dataops_lote_and_facts_alignment.sql
-- Propósito:
--   1. Crear tabla public.lote para ingesta y navegación multi-archivo (#17, #19).
--   2. Alinear dim_origen_documental con id_lote, tipo_fuente, tipo_escala
--      nullable, institucion, periodo y hash_sha256 (#8, #16, #18, #19).
--   3. Alinear fact_rendimiento_academico, fact_situacion_financiera y dim_modulo
--      con los modelos ORM de SQLAlchemy (#9, #20).
--   4. Formalizar staging_registros_crudos, stg_entidad_no_resuelta y
--      log_inconsistencias con motivo, payload_json (JSONB), registro_origen_id
--      y estado_resolucion (#11, #12).
-- ============================================================================

BEGIN;

-- 1. Tabla de Lotes Multi-Archivo (#17, #19)
CREATE TABLE IF NOT EXISTS public.lote (
    id_lote SERIAL PRIMARY KEY,
    institucion VARCHAR(100) NOT NULL,
    periodo VARCHAR(30) NOT NULL,
    estado VARCHAR(30) DEFAULT 'PROCESADO',
    total_archivos INT DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lote_institucion_periodo ON public.lote(institucion, periodo);

-- 2. Asegurar cat_institucion para FK de dim_modulo (#20)
CREATE TABLE IF NOT EXISTS public.cat_institucion (
    id_institucion SERIAL PRIMARY KEY,
    nombre_institucion VARCHAR(100) NOT NULL UNIQUE,
    sigla VARCHAR(30),
    tipo_escala_default VARCHAR(20) DEFAULT 'CENTESIMAL_100',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.cat_institucion (nombre_institucion, sigla, tipo_escala_default)
VALUES
    ('GiraGroup', 'GG', 'CENTESIMAL_100'),
    ('Escuela de Negocios y Postgrado', 'ENP', 'CENTESIMAL_100'),
    ('Facultad de Ciencias de la Salud', 'FCS', 'CENTESIMAL_100')
ON CONFLICT (nombre_institucion) DO NOTHING;

-- 3. Alineación de dim_modulo (#20)
ALTER TABLE public.dim_modulo
    ADD COLUMN IF NOT EXISTS nombre_institucion VARCHAR(200) NOT NULL DEFAULT 'GiraGroup';

ALTER TABLE public.dim_modulo
    ADD COLUMN IF NOT EXISTS id_institucion INT REFERENCES public.cat_institucion(id_institucion) ON DELETE SET NULL;

-- 4. Alteración de dim_origen_documental (#8, #16, #18, #19)
ALTER TABLE public.dim_origen_documental
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_doc;

ALTER TABLE public.dim_origen_documental
    ALTER COLUMN tipo_documento TYPE VARCHAR(50);

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS id_lote INT REFERENCES public.lote(id_lote) ON DELETE SET NULL;

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS tipo_fuente VARCHAR(30);

ALTER TABLE public.dim_origen_documental
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_fuente;

ALTER TABLE public.dim_origen_documental
    ADD CONSTRAINT chk_dim_origen_tipo_fuente
    CHECK (tipo_fuente IS NULL OR tipo_fuente IN ('ACTA', 'COBRANZA', 'ADMISION', 'MOODLE'));

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS tipo_escala VARCHAR(20);

ALTER TABLE public.dim_origen_documental
    ALTER COLUMN tipo_escala DROP DEFAULT;

ALTER TABLE public.dim_origen_documental
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_escala;

ALTER TABLE public.dim_origen_documental
    ADD CONSTRAINT chk_dim_origen_tipo_escala
    CHECK (tipo_escala IS NULL OR tipo_escala IN ('CENTESIMAL_100', 'DECIMAL_10', 'VIGESIMAL_20'));

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS institucion VARCHAR(100);

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS periodo VARCHAR(30);

ALTER TABLE public.dim_origen_documental
    ADD COLUMN IF NOT EXISTS hash_sha256 VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_dim_origen_id_lote ON public.dim_origen_documental(id_lote);
CREATE INDEX IF NOT EXISTS idx_dim_origen_hash_sha256 ON public.dim_origen_documental(hash_sha256);

-- 5. Alineación de fact_rendimiento_academico (#20)
ALTER TABLE public.fact_rendimiento_academico
    ADD COLUMN IF NOT EXISTS fk_estado VARCHAR(1) DEFAULT 'A';

ALTER TABLE public.fact_rendimiento_academico
    ADD COLUMN IF NOT EXISTS tipo_alerta VARCHAR(30);

-- 6. Adecuación de fact_situacion_financiera (#9, #20)
ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS id_modulo INT REFERENCES public.dim_modulo(id_modulo) ON DELETE SET NULL;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS id_categoria_fin INT REFERENCES public.dim_categoria_financiera(id_categoria) ON DELETE SET NULL;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS id_documento INT REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS monto_pagado NUMERIC(12, 2) DEFAULT 0.00;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS concepto VARCHAR(150);

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS cuotas_impagas INT DEFAULT 0;

ALTER TABLE public.fact_situacion_financiera
    ALTER COLUMN tipo_alerta TYPE VARCHAR(30);

ALTER TABLE public.fact_situacion_financiera
    ALTER COLUMN tipo_alerta SET DEFAULT 'NORMAL';

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS nivel_confianza_ia NUMERIC(5, 4) DEFAULT 1.0000;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS requiere_revision BOOLEAN DEFAULT FALSE;

ALTER TABLE public.fact_situacion_financiera
    ADD COLUMN IF NOT EXISTS fk_estado VARCHAR(1) DEFAULT 'A';

ALTER TABLE public.fact_situacion_financiera
    DROP CONSTRAINT IF EXISTS uq_fact_situacion_financiera_estudiante_tiempo;

ALTER TABLE public.fact_situacion_financiera
    DROP CONSTRAINT IF EXISTS uq_fact_financiera_est_mod_tiempo;

DELETE FROM public.fact_situacion_financiera a USING public.fact_situacion_financiera b
WHERE a.id_hecho_fin < b.id_hecho_fin
  AND a.id_estudiante = b.id_estudiante
  AND COALESCE(a.id_modulo, 0) = COALESCE(b.id_modulo, 0)
  AND a.id_tiempo = b.id_tiempo;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_fin_est_mod_tiempo
ON public.fact_situacion_financiera (id_estudiante, COALESCE(id_modulo, 0), id_tiempo);

-- 7. Tablas de Staging e Inconsistencias (#11, #12)
CREATE TABLE IF NOT EXISTS public.staging_registros_crudos (
    id SERIAL PRIMARY KEY,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
    hoja VARCHAR(200),
    bloque_id INTEGER,
    categoria VARCHAR(50),
    texto_plano TEXT,
    n_filas INTEGER,
    fila_inicio INTEGER,
    fila_fin INTEGER,
    es_ruido BOOLEAN DEFAULT FALSE,
    requiere_revision BOOLEAN DEFAULT FALSE,
    score_confianza NUMERIC(5, 4) DEFAULT 1.0,
    motivo VARCHAR(100),
    payload_json JSONB,
    registro_origen_id INT REFERENCES public.staging_registros_crudos(id) ON DELETE CASCADE,
    estado_resolucion VARCHAR(30) DEFAULT 'PENDIENTE',
    resuelto BOOLEAN DEFAULT FALSE,
    resuelto_por INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    resuelto_en TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS requiere_revision BOOLEAN DEFAULT FALSE;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS score_confianza NUMERIC(5, 4) DEFAULT 1.0;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS motivo VARCHAR(100);
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS payload_json JSONB;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS registro_origen_id INT REFERENCES public.staging_registros_crudos(id) ON DELETE CASCADE;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS estado_resolucion VARCHAR(30) DEFAULT 'PENDIENTE';
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS resuelto BOOLEAN DEFAULT FALSE;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS resuelto_por INTEGER REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.staging_registros_crudos
    ADD COLUMN IF NOT EXISTS resuelto_en TIMESTAMP;

CREATE TABLE IF NOT EXISTS public.stg_entidad_no_resuelta (
    id_staging SERIAL PRIMARY KEY,
    id_documento INT REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
    tipo_entidad VARCHAR(50) NOT NULL,
    texto_original TEXT NOT NULL,
    ci_temporal VARCHAR(150),
    mejor_candidato TEXT,
    score_fuzzy NUMERIC(5, 2),
    fk_estado VARCHAR(1) DEFAULT 'C',
    nivel_confianza NUMERIC(5, 4),
    resuelto BOOLEAN DEFAULT FALSE,
    resuelto_por INT REFERENCES public.users(id) ON DELETE SET NULL,
    resuelto_en TIMESTAMP,
    id_dimension_resuelta INT,
    motivo VARCHAR(100),
    payload_json JSONB,
    registro_origen_id INT REFERENCES public.staging_registros_crudos(id) ON DELETE CASCADE,
    estado_resolucion VARCHAR(30) DEFAULT 'PENDIENTE',
    lock_usuario_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    lock_expira TIMESTAMP,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS motivo VARCHAR(100);
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS payload_json JSONB;
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS registro_origen_id INT REFERENCES public.staging_registros_crudos(id) ON DELETE CASCADE;
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS estado_resolucion VARCHAR(30) DEFAULT 'PENDIENTE';
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS lock_usuario_id INT REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS lock_expira TIMESTAMP;
ALTER TABLE public.stg_entidad_no_resuelta
    ADD COLUMN IF NOT EXISTS version INT DEFAULT 1;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'stg_entidad_no_resuelta'
          AND column_name = 'payload_json'
          AND data_type IN ('text', 'character varying')
    ) THEN
        ALTER TABLE public.stg_entidad_no_resuelta
            ALTER COLUMN payload_json TYPE JSONB
            USING CASE
                WHEN payload_json IS NULL OR btrim(payload_json) = '' THEN NULL
                ELSE payload_json::jsonb
            END;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.log_inconsistencias (
    id_inconsistencia SERIAL PRIMARY KEY,
    id_documento INT REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
    fila_origen INT,
    campo_afectado VARCHAR(100) NOT NULL,
    valor_recibido TEXT,
    valor_esperado TEXT,
    tipo_regla VARCHAR(50) NOT NULL,
    severidad VARCHAR(20) NOT NULL DEFAULT 'ALTA',
    estado_resolucion VARCHAR(30) NOT NULL DEFAULT 'BLOQUEADO',
    descripcion TEXT,
    detectado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resuelto_en TIMESTAMP,
    resuelto_por INT REFERENCES public.users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_log_inconsistencias_doc ON public.log_inconsistencias(id_documento);
CREATE INDEX IF NOT EXISTS idx_log_inconsistencias_estado ON public.log_inconsistencias(estado_resolucion);

-- 8. RLS en tablas nuevas
ALTER TABLE public.lote ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.log_inconsistencias ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'lote_select_all' AND tablename = 'lote') THEN
        CREATE POLICY lote_select_all ON public.lote FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'lote_all_access' AND tablename = 'lote') THEN
        CREATE POLICY lote_all_access ON public.lote FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'log_inc_select_all' AND tablename = 'log_inconsistencias') THEN
        CREATE POLICY log_inc_select_all ON public.log_inconsistencias FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'log_inc_all_access' AND tablename = 'log_inconsistencias') THEN
        CREATE POLICY log_inc_all_access ON public.log_inconsistencias FOR ALL USING (true);
    END IF;
END $$;

COMMIT;
