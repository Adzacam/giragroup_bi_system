-- ============================================================================
-- Migración Versionada: 002_beto_ner_governance_schema.sql
-- Propósito: Implementar gobernanza DDL para BETO NER, catálogos canónicos,
--            tablas de alias tipadas por contexto, normalización de CI,
--            soporte de instituciones, trazabilidad de fusiones y RLS.
-- Sistema: GiraGroup BI System (PostgreSQL 16)
-- ============================================================================

BEGIN;

-- 1. Catálogo de Instituciones
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

-- 2. Catálogo de Programas Académicos (con pos_code y tipo_escala)
CREATE TABLE IF NOT EXISTS public.cat_programa (
    id_programa SERIAL PRIMARY KEY,
    pos_code VARCHAR(50) NOT NULL UNIQUE,
    nombre_programa VARCHAR(255) NOT NULL,
    version INT DEFAULT 1,
    nombre_completo_raw VARCHAR(300),
    id_escuela INT,
    id_tipo_programa INT,
    id_modalidad INT,
    tipo_escala VARCHAR(20) DEFAULT 'CENTESIMAL_100',
    inversion_base NUMERIC(12, 2) DEFAULT 0.00,
    punto_equilibrio INT DEFAULT 0,
    horas_totales INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.cat_programa 
    ADD COLUMN IF NOT EXISTS tipo_escala VARCHAR(20) DEFAULT 'CENTESIMAL_100';

INSERT INTO public.cat_programa (pos_code, nombre_programa, tipo_escala)
VALUES 
    ('POS-101', 'Maestría en Dirección y Gestión Empresarial (MBA)', 'CENTESIMAL_100'),
    ('POS-202', 'Diplomado en Inteligencia Artificial & Big Data', 'CENTESIMAL_100'),
    ('POS-303', 'Programa Experto en Ciberseguridad & Redes', 'CENTESIMAL_100'),
    ('POS-404', 'Diplomado en Medicina Estética & Antienvejecimiento', 'CENTESIMAL_100')
ON CONFLICT (pos_code) DO NOTHING;

-- 3. Catálogo de Categorías Financieras
CREATE TABLE IF NOT EXISTS public.cat_categoria_financiera (
    id_categoria_fin SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre_categoria VARCHAR(100) NOT NULL,
    tipo_flujo VARCHAR(30) NOT NULL DEFAULT 'INGRESO', -- INGRESO / EGRESO / SALDO / AJUSTE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.cat_categoria_financiera (codigo, nombre_categoria, tipo_flujo)
VALUES 
    ('ING-COB-01', 'Cobranza Cuota Mensual', 'INGRESO'),
    ('ING-MAT-01', 'Matrícula Inicial', 'INGRESO'),
    ('ING-CER-01', 'Trámite de Certificación y Titulación', 'INGRESO'),
    ('EGR-DOC-01', 'Honorarios Docente', 'EGRESO'),
    ('EGR-OPE-01', 'Gasto Operativo y Plataforma', 'EGRESO')
ON CONFLICT (codigo) DO NOTHING;

-- 4. Enlace entre dim_categoria_financiera y cat_categoria_financiera
ALTER TABLE public.dim_categoria_financiera 
    ADD COLUMN IF NOT EXISTS id_cat_categoria_fin INT REFERENCES public.cat_categoria_financiera(id_categoria_fin);

-- 5. Asegurar campos en cat_docente y cat_modulo
ALTER TABLE public.cat_docente 
    ADD COLUMN IF NOT EXISTS nombre_completo VARCHAR(200);

UPDATE public.cat_docente 
SET nombre_completo = nombre_canonico 
WHERE nombre_completo IS NULL AND nombre_canonico IS NOT NULL;

ALTER TABLE public.cat_modulo 
    ADD COLUMN IF NOT EXISTS nombre_modulo VARCHAR(255);

UPDATE public.cat_modulo 
SET nombre_modulo = nombre_canonico 
WHERE nombre_modulo IS NULL AND nombre_canonico IS NOT NULL;

-- 6. Actualización de dim_estudiante (CI normalizado, Institución, Trazabilidad)
ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS ci VARCHAR(50);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS ci_numero VARCHAR(30);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS ci_complemento VARCHAR(10);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS id_temporal VARCHAR(100);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS identidad_verificada BOOLEAN DEFAULT FALSE;

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS id_institucion INT REFERENCES public.cat_institucion(id_institucion);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS programa_origen VARCHAR(200);

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS deprecado BOOLEAN DEFAULT FALSE;

ALTER TABLE public.dim_estudiante 
    ADD COLUMN IF NOT EXISTS fusionado_en INT REFERENCES public.dim_estudiante(id_estudiante);

-- Normalizar ci_numero y ci_complemento desde ci existente
UPDATE public.dim_estudiante
SET ci_numero = regexp_replace(split_part(ci, ' ', 1), '[^0-9]', '', 'g'),
    ci_complemento = CASE WHEN position(' ' in ci) > 0 THEN split_part(ci, ' ', 2) ELSE NULL END
WHERE ci IS NOT NULL AND ci_numero IS NULL;

-- Índice único parcial sobre ci_numero para deduplicación estricta
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_estudiante_ci_numero 
ON public.dim_estudiante (ci_numero) 
WHERE deprecado = FALSE AND ci_numero IS NOT NULL AND length(ci_numero) >= 5;

-- 7. Actualización de dim_modulo y dim_docente con FKs al catálogo maestro
ALTER TABLE public.dim_modulo 
    ADD COLUMN IF NOT EXISTS id_cat_modulo INT REFERENCES public.cat_modulo(id_modulo);

ALTER TABLE public.dim_docente 
    ADD COLUMN IF NOT EXISTS id_cat_docente INT REFERENCES public.cat_docente(id_docente);

-- 8. Actualización de fact_situacion_financiera (id_modulo y Unicidad de Hechos)
ALTER TABLE public.fact_situacion_financiera 
    ADD COLUMN IF NOT EXISTS id_modulo INT REFERENCES public.dim_modulo(id_modulo);

-- Reemplazar unicidad antigua por unicidad (id_estudiante, id_modulo, id_tiempo)
ALTER TABLE public.fact_situacion_financiera 
    DROP CONSTRAINT IF EXISTS uq_fact_situacion_financiera_estudiante_tiempo;

ALTER TABLE public.fact_situacion_financiera 
    DROP CONSTRAINT IF EXISTS uq_fact_financiera_est_mod_tiempo;

-- Limpieza de duplicados previos si existieran antes de añadir la constraint
DELETE FROM public.fact_situacion_financiera a USING public.fact_situacion_financiera b
WHERE a.id_hecho_fin < b.id_hecho_fin
  AND a.id_estudiante = b.id_estudiante
  AND (a.id_modulo = b.id_modulo OR (a.id_modulo IS NULL AND b.id_modulo IS NULL))
  AND a.id_tiempo = b.id_tiempo;

ALTER TABLE public.fact_situacion_financiera 
    ADD CONSTRAINT uq_fact_financiera_est_mod_tiempo 
    UNIQUE (id_estudiante, id_modulo, id_tiempo);

-- 9. Normalización y CHECK de dim_origen_documental
ALTER TABLE public.dim_origen_documental 
    ADD COLUMN IF NOT EXISTS tipo_escala VARCHAR(20) DEFAULT 'CENTESIMAL_100';

ALTER TABLE public.dim_origen_documental 
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_escala;

ALTER TABLE public.dim_origen_documental 
    ADD CONSTRAINT chk_dim_origen_tipo_escala 
    CHECK (tipo_escala IS NULL OR tipo_escala IN ('CENTESIMAL_100', 'DECIMAL_10', 'VIGESIMAL_20'));

ALTER TABLE public.dim_origen_documental 
    DROP CONSTRAINT IF EXISTS chk_dim_origen_tipo_doc;

ALTER TABLE public.dim_origen_documental 
    ADD CONSTRAINT chk_dim_origen_tipo_doc 
    CHECK (tipo_documento IN ('EXCEL', 'CSV', 'MOODLE', 'SHEET', 'XML', 'GOOGLE_FORMS'));

-- 10. Tablas fuertemente tipadas para alias por contexto
-- En cat_alias_modulo: UNIQUE (id_programa, alias_texto)
CREATE TABLE IF NOT EXISTS public.cat_alias_modulo (
    id_alias SERIAL PRIMARY KEY,
    id_modulo INT NOT NULL REFERENCES public.cat_modulo(id_modulo) ON DELETE CASCADE,
    id_programa INT NOT NULL REFERENCES public.cat_programa(id_programa) ON DELETE CASCADE,
    alias_texto VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cat_alias_modulo_prog_alias UNIQUE (id_programa, alias_texto)
);

CREATE TABLE IF NOT EXISTS public.cat_alias_docente (
    id_alias SERIAL PRIMARY KEY,
    id_docente INT NOT NULL REFERENCES public.cat_docente(id_docente) ON DELETE CASCADE,
    alias_texto VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.cat_alias_programa (
    id_alias SERIAL PRIMARY KEY,
    id_programa INT NOT NULL REFERENCES public.cat_programa(id_programa) ON DELETE CASCADE,
    alias_texto VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.cat_alias_financiero (
    id_alias SERIAL PRIMARY KEY,
    id_categoria_fin INT NOT NULL REFERENCES public.cat_categoria_financiera(id_categoria_fin) ON DELETE CASCADE,
    alias_texto VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Habilitación de Row-Level Security (RLS) y Políticas en Tablas Nuevas y Staging
ALTER TABLE public.cat_alias_modulo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cat_alias_docente ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cat_alias_programa ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cat_alias_financiero ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staging_registros_crudos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stg_entidad_no_resuelta ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_mod_select') THEN
        CREATE POLICY cat_alias_mod_select ON public.cat_alias_modulo FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_mod_all') THEN
        CREATE POLICY cat_alias_mod_all ON public.cat_alias_modulo FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_doc_select') THEN
        CREATE POLICY cat_alias_doc_select ON public.cat_alias_docente FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_doc_all') THEN
        CREATE POLICY cat_alias_doc_all ON public.cat_alias_docente FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_prog_select') THEN
        CREATE POLICY cat_alias_prog_select ON public.cat_alias_programa FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_prog_all') THEN
        CREATE POLICY cat_alias_prog_all ON public.cat_alias_programa FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_fin_select') THEN
        CREATE POLICY cat_alias_fin_select ON public.cat_alias_financiero FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'cat_alias_fin_all') THEN
        CREATE POLICY cat_alias_fin_all ON public.cat_alias_financiero FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'stg_crudos_select') THEN
        CREATE POLICY stg_crudos_select ON public.staging_registros_crudos FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'stg_crudos_all') THEN
        CREATE POLICY stg_crudos_all ON public.staging_registros_crudos FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'stg_no_resuelta_select') THEN
        CREATE POLICY stg_no_resuelta_select ON public.stg_entidad_no_resuelta FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'stg_no_resuelta_all') THEN
        CREATE POLICY stg_no_resuelta_all ON public.stg_entidad_no_resuelta FOR ALL USING (true);
    END IF;
END $$;

COMMIT;
