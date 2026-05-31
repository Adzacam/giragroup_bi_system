-- ─────────────────────────────────────────
-- DIMENSIONES
-- ─────────────────────────────────────────

CREATE TABLE dim_tiempo (
    id_tiempo        SERIAL PRIMARY KEY,
    gestion          INT         NOT NULL,
    semestre         INT,
    mes              VARCHAR(20)
);

CREATE TABLE dim_estudiante (
    id_estudiante    SERIAL PRIMARY KEY,
    nombre_completo  VARCHAR(200) NOT NULL,
    codigo_estudiante VARCHAR(50)
);

CREATE TABLE dim_docente (
    id_docente       SERIAL PRIMARY KEY,
    nombre_completo  VARCHAR(200) NOT NULL,
    area_especialidad VARCHAR(200)
);

CREATE TABLE dim_modulo (
    id_modulo        SERIAL PRIMARY KEY,
    nombre_modulo    VARCHAR(200) NOT NULL,
    nombre_institucion VARCHAR(200) NOT NULL, 
    programa         VARCHAR(200)             
);

CREATE TABLE dim_origen_documental (
    id_documento     SERIAL PRIMARY KEY,
    tipo_documento   VARCHAR(10) CHECK (tipo_documento IN ('SHEET', 'FORM', 'MOODLE', 'XLSX')),
    nombre_archivo   VARCHAR(500),
    fecha_procesamiento TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- TABLA TRANSACCIONAL (3FN) — para auth
-- ─────────────────────────────────────────

CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(100) UNIQUE NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    role             VARCHAR(20) CHECK (role IN ('coordinador', 'administrativo', 'marketing', 'admin')),
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- TABLAS DE HECHOS (CONSTELACIÓN)
-- ─────────────────────────────────────────

-- TABLA DE HECHOS 1: RENDIMIENTO ACADÉMICO
CREATE TABLE fact_rendimiento_academico (
    id_hecho_aca          SERIAL PRIMARY KEY,
    id_estudiante         INT REFERENCES dim_estudiante(id_estudiante),
    id_docente            INT REFERENCES dim_docente(id_docente),
    id_modulo             INT REFERENCES dim_modulo(id_modulo),
    id_tiempo             INT REFERENCES dim_tiempo(id_tiempo),
    id_documento          INT REFERENCES dim_origen_documental(id_documento),
    id_usuario_carga      INT REFERENCES users(id),
    nota_final            NUMERIC(5,2),
    asistencia_pct        NUMERIC(5,2),
    nivel_confianza_ia    NUMERIC(5,4),
    requiere_revision     BOOLEAN DEFAULT FALSE,
    created_at            TIMESTAMP DEFAULT NOW()
);

-- TABLA DE HECHOS 2: SITUACIÓN FINANCIERA
CREATE TABLE fact_situacion_financiera (
    id_hecho_fin          SERIAL PRIMARY KEY,
    id_estudiante         INT REFERENCES dim_estudiante(id_estudiante),
    id_tiempo             INT REFERENCES dim_tiempo(id_tiempo),
    monto_deuda           NUMERIC(10,2),
    cuotas_impagas        INT,
    estado_cartera        VARCHAR(20),
    tipo_alerta           VARCHAR(20),
    fecha_registro        TIMESTAMP DEFAULT NOW()
);