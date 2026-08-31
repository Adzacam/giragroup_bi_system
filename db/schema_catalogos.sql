-- =============================================================================
-- BASE DE DATOS DE CATÁLOGOS DE REFERENCIA INSTITUCIONAL (3NF)
-- Base de Datos: giragroup_catalog_db
-- =============================================================================

-- 1. Escuelas Académicas
CREATE TABLE IF NOT EXISTS public.cat_escuela (
    id_escuela SERIAL PRIMARY KEY,
    nombre_escuela VARCHAR(100) NOT NULL UNIQUE,
    sigla VARCHAR(20)
);

-- 2. Tipos de Programa
CREATE TABLE IF NOT EXISTS public.cat_tipo_programa (
    id_tipo_programa SERIAL PRIMARY KEY,
    nombre_tipo VARCHAR(100) NOT NULL UNIQUE
);

-- 3. Modalidades
CREATE TABLE IF NOT EXISTS public.cat_modalidad (
    id_modalidad SERIAL PRIMARY KEY,
    nombre_modalidad VARCHAR(100) NOT NULL UNIQUE
);

-- 4. Programas Canónicos (con versión y vínculo a escuela, tipo y modalidad)
CREATE TABLE IF NOT EXISTS public.cat_programa (
    id_programa SERIAL PRIMARY KEY,
    pos_code VARCHAR(50) NOT NULL UNIQUE,
    nombre_programa VARCHAR(255) NOT NULL,
    version INT DEFAULT 1,
    nombre_completo_raw VARCHAR(300),
    id_escuela INT REFERENCES public.cat_escuela(id_escuela) ON DELETE RESTRICT,
    id_tipo_programa INT REFERENCES public.cat_tipo_programa(id_tipo_programa) ON DELETE RESTRICT,
    id_modalidad INT REFERENCES public.cat_modalidad(id_modalidad) ON DELETE RESTRICT,
    inversion_base NUMERIC(12, 2) DEFAULT 0.00,
    punto_equilibrio INT DEFAULT 0,
    horas_totales INT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cat_prg_pos ON public.cat_programa(pos_code);
CREATE INDEX IF NOT EXISTS idx_cat_prg_nombre ON public.cat_programa(nombre_programa);

-- 5. Docentes Institucionales
CREATE TABLE IF NOT EXISTS public.cat_docente (
    id_docente SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL UNIQUE,
    email VARCHAR(150),
    celular VARCHAR(50),
    grado_academico VARCHAR(100),
    tipo_docente VARCHAR(50) DEFAULT 'TITULAR'
);
CREATE INDEX IF NOT EXISTS idx_cat_doc_nombre ON public.cat_docente(nombre_completo);

-- 6. Módulos por Programa
CREATE TABLE IF NOT EXISTS public.cat_modulo (
    id_modulo SERIAL PRIMARY KEY,
    id_programa INT NOT NULL REFERENCES public.cat_programa(id_programa) ON DELETE CASCADE,
    nro_modulo INT NOT NULL,
    nombre_modulo VARCHAR(255) NOT NULL,
    horas_modulo NUMERIC(6, 2) DEFAULT 0,
    pago_docente_base NUMERIC(10, 2) DEFAULT 0,
    CONSTRAINT uq_cat_modulo_programa_nro UNIQUE (id_programa, nro_modulo)
);

-- 7. Criterios Académicos y Estados
CREATE TABLE IF NOT EXISTS public.cat_estado_academico (
    id_estado_academico SERIAL PRIMARY KEY,
    nombre_estado VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS public.cat_estado_reprobado (
    id_estado_reprobado SERIAL PRIMARY KEY,
    nombre_detalle VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS public.cat_estado_arca (
    id_estado_arca SERIAL PRIMARY KEY,
    nombre_arca VARCHAR(100) NOT NULL UNIQUE
);

-- 8. Clasificación de Cartera de Cobranzas
CREATE TABLE IF NOT EXISTS public.cat_tipo_cartera (
    id_cartera SERIAL PRIMARY KEY,
    nombre_cartera VARCHAR(100) NOT NULL UNIQUE,
    dias_mora_min INT NOT NULL,
    dias_mora_max INT NOT NULL,
    descripcion VARCHAR(255)
);

-- 9. Metas de Gestión Presupuestaria
CREATE TABLE IF NOT EXISTS public.ref_metas_gestion (
    id_meta SERIAL PRIMARY KEY,
    gestion INT NOT NULL,
    mes INT NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    monto_meta_ingreso NUMERIC(14, 2) DEFAULT 0,
    monto_ejecutado NUMERIC(14, 2) DEFAULT 0,
    ebitda_meta_pct NUMERIC(6, 4),
    ebitda_ejecutado_pct NUMERIC(6, 4),
    CONSTRAINT uq_ref_metas_gestion_mes_cat UNIQUE (gestion, mes, categoria)
);
