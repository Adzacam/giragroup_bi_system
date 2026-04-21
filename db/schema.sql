-- ─────────────────────────────────────────
-- DIMENSIONES
-- ─────────────────────────────────────────

CREATE TABLE dim_tiempo (
    id_tiempo        SERIAL PRIMARY KEY,
    gestion          INT         NOT NULL,
    semestre         INT,
    mes              VARCHAR(20)
);

CREATE TABLE dim_institucion (
    id_institucion   SERIAL PRIMARY KEY,
    nombre           VARCHAR(200) NOT NULL   -- ej. "Unifranz", "Univ. Bolivariana"
);

CREATE TABLE dim_estudiante (
    id_estudiante    SERIAL PRIMARY KEY,
    nombre_completo  VARCHAR(200) NOT NULL,
    codigo_estudiante VARCHAR(50)
    -- programa se elimina aquí, vive en dim_modulo
);

CREATE TABLE dim_docente (
    id_docente       SERIAL PRIMARY KEY,
    nombre_completo  VARCHAR(200) NOT NULL,
    area_especialidad VARCHAR(200)
);

CREATE TABLE dim_modulo (
    id_modulo        SERIAL PRIMARY KEY,
    nombre_modulo    VARCHAR(200) NOT NULL,
    id_institucion   INT REFERENCES dim_institucion(id_institucion),
    programa         VARCHAR(200)   -- diplomado / experto / curso
);

CREATE TABLE dim_origen_documental (
    id_documento     SERIAL PRIMARY KEY,
    tipo_documento   VARCHAR(10) CHECK (tipo_documento IN ('PDF','SHEET','FORM','DOCX','XLSX')),
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
    role             VARCHAR(20) CHECK (role IN ('coordinador','administrativo')),
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- TABLA DE HECHOS
-- ─────────────────────────────────────────

CREATE TABLE fact_rendimiento_academico (
    id_hecho              SERIAL PRIMARY KEY,
    id_estudiante         INT REFERENCES dim_estudiante(id_estudiante),
    id_docente            INT REFERENCES dim_docente(id_docente),
    id_modulo             INT REFERENCES dim_modulo(id_modulo),
    id_tiempo             INT REFERENCES dim_tiempo(id_tiempo),
    id_documento          INT REFERENCES dim_origen_documental(id_documento),
    id_usuario_carga      INT REFERENCES users(id),    -- auditoría GIRA-20
    nota_final            NUMERIC(5,2),
    porcentaje_asistencia NUMERIC(5,2),
    nivel_confianza_ia    NUMERIC(5,4),                -- 4 decimales: 0.8523
    requiere_revision     BOOLEAN DEFAULT FALSE,       -- GIRA-22: confianza < 0.60
    created_at            TIMESTAMP DEFAULT NOW()
);