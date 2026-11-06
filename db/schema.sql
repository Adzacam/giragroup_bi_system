-- =============================================================================
-- ESQUEMA CONSTELACIÓN - GIRAGROUP BI 
-- SCRIPT DE CREACIÓN PARA POSTGRESQL
-- =============================================================================

-- ==========================================
-- 0. LIMPIEZA PREVIA (DROP TABLES)
-- ==========================================
DO $$ 
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', r.tablename);
  END LOOP;
END $$;

-- ==========================================
-- 1. TABLA DE USUARIOS / SISTEMA / LOTES
-- ==========================================
CREATE TABLE public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(30),
    is_active BOOLEAN DEFAULT TRUE,
    is_mfa_enabled BOOLEAN DEFAULT TRUE,
    otp_code_hash VARCHAR(255),
    otp_expires_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_by_id INTEGER REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_users_role CHECK (role IN ('ADMIN','AUDITOR_CALIDAD','DIRECTOR_ACADEMICO','ANALISTA_FINANCIERO','ANALISTA_MARKETING'))
);

CREATE TABLE public.notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id),
    role_target VARCHAR(50),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    link VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.lote (
    id_lote SERIAL PRIMARY KEY,
    institucion VARCHAR(100) NOT NULL,
    periodo VARCHAR(30) NOT NULL,
    estado VARCHAR(30) DEFAULT 'PROCESADO',
    total_archivos INT DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lote_institucion_periodo ON public.lote(institucion, periodo);

CREATE TABLE IF NOT EXISTS public.cat_institucion (
    id_institucion SERIAL PRIMARY KEY,
    nombre_institucion VARCHAR(100) NOT NULL UNIQUE,
    sigla VARCHAR(30),
    tipo_escala_default VARCHAR(20) DEFAULT 'CENTESIMAL_100',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.cat_institucion (nombre_institucion, sigla, tipo_escala_default)
VALUES
    ('GiraGroup Posgrado', 'GG', 'CENTESIMAL_100'),
    ('Escuela de Negocios y Postgrado', 'ENP', 'CENTESIMAL_100'),
    ('Facultad de Ciencias de la Salud', 'FCS', 'CENTESIMAL_100')
ON CONFLICT (nombre_institucion) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.cat_categoria_financiera (
    id_categoria_fin SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre_categoria VARCHAR(100) NOT NULL,
    tipo_flujo VARCHAR(30) NOT NULL DEFAULT 'INGRESO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 2. DIMENSIONES (DIM)
-- ==========================================
CREATE TABLE public.dim_tiempo (
    id_tiempo       INTEGER PRIMARY KEY,         -- YYYYMMDD (ej: 20250315)
    fecha           DATE NOT NULL UNIQUE,
    gestion         INT NOT NULL,                -- 2022 .. 2027
    semestre        INT NOT NULL,                -- 1, 2
    trimestre       INT NOT NULL,                -- 1 .. 4
    mes             INT NOT NULL,                -- 1 .. 12
    nombre_mes      VARCHAR(20) NOT NULL,        -- 'Enero', 'Febrero'...
    semana_iso      INT NOT NULL,                -- 1 .. 53
    dia_mes         INT NOT NULL,                -- 1 .. 31
    dia_semana      INT NOT NULL,                -- 1=Lunes .. 7=Domingo
    nombre_dia      VARCHAR(20) NOT NULL,        -- 'Lunes', 'Martes'...
    es_fin_semana   BOOLEAN NOT NULL,            -- TRUE si sábado o domingo
    periodo_mes     VARCHAR(7) NOT NULL          -- '2026-01'
);
CREATE INDEX idx_dim_tiempo_periodo ON public.dim_tiempo(periodo_mes);

CREATE TABLE public.dim_estudiante (
    id_estudiante SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    codigo_estudiante VARCHAR(50),
    ci VARCHAR(50),
    ci_numero VARCHAR(30),
    ci_complemento VARCHAR(10),
    id_temporal VARCHAR(100),
    identidad_verificada BOOLEAN DEFAULT FALSE,
    id_institucion INT REFERENCES public.cat_institucion(id_institucion) ON DELETE SET NULL,
    programa_origen VARCHAR(200),
    deprecado BOOLEAN DEFAULT FALSE,
    fusionado_en INT REFERENCES public.dim_estudiante(id_estudiante) ON DELETE SET NULL,
    genero VARCHAR(20),
    ciudad VARCHAR(100),
    nivel_academico VARCHAR(100),
    edad INTEGER,
    ocupacion VARCHAR(100),
    estado_civil VARCHAR(50)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_estudiante_ci_numero 
ON public.dim_estudiante (ci_numero) 
WHERE deprecado = FALSE AND ci_numero IS NOT NULL AND length(ci_numero) >= 5;

-- Catálogos canónicos de docentes y módulos (migración 002): dim_docente y dim_modulo los referencian
CREATE TABLE public.cat_docente (
    id_docente SERIAL PRIMARY KEY,
    codigo_docente VARCHAR(50),
    nombre_canonico VARCHAR(200) NOT NULL,
    area VARCHAR(100) DEFAULT 'Académico',
    nombre_completo VARCHAR(200)
);

CREATE TABLE public.cat_modulo (
    id_modulo SERIAL PRIMARY KEY,
    codigo_modulo VARCHAR(50),
    nombre_canonico VARCHAR(200) NOT NULL,
    area VARCHAR(100) DEFAULT 'General',
    nombre_modulo VARCHAR(255)
);

CREATE TABLE public.dim_docente (
    id_docente SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL DEFAULT 'Docente Generico',
    area_especialidad VARCHAR(200) DEFAULT 'Generico',
    id_cat_docente INT REFERENCES public.cat_docente(id_docente) ON DELETE SET NULL
);

CREATE TABLE public.dim_modulo (
    id_modulo SERIAL PRIMARY KEY,
    nombre_modulo VARCHAR(200) NOT NULL DEFAULT 'Modulo Generico',
    nombre_institucion VARCHAR(200) NOT NULL DEFAULT 'GiraGroup Posgrado',
    id_institucion INT REFERENCES public.cat_institucion(id_institucion) ON DELETE SET NULL,
    programa VARCHAR(200) DEFAULT 'General',
    pos_code VARCHAR(50),
    id_cat_modulo INT REFERENCES public.cat_modulo(id_modulo) ON DELETE SET NULL
);

CREATE TABLE public.dim_origen_documental (
    id_documento SERIAL PRIMARY KEY,
    id_lote INT REFERENCES public.lote(id_lote) ON DELETE SET NULL,
    tipo_documento VARCHAR(50) DEFAULT 'SHEET',
    tipo_fuente VARCHAR(30) CHECK (tipo_fuente IS NULL OR tipo_fuente IN ('ACTA', 'COBRANZA', 'ADMISION', 'MOODLE', 'EVALUACION_DOCENTE', 'EGRESOS', 'TECHOS', 'PLANIFICACION', 'MARKETING', 'RENTABILIDAD', 'ERROR', 'RECHAZADO', 'DUPLICADO', 'SIN_RECONOCER')),
    tipo_escala VARCHAR(20) CHECK (tipo_escala IS NULL OR tipo_escala IN ('CENTESIMAL_100', 'DECIMAL_10', 'VIGESIMAL_20')),
    nombre_archivo VARCHAR(500) DEFAULT 'archivo_generico',
    institucion VARCHAR(100),
    periodo VARCHAR(30),
    hash_sha256 VARCHAR(64),
    fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dim_origen_id_lote ON public.dim_origen_documental(id_lote);
CREATE INDEX IF NOT EXISTS idx_dim_origen_hash_sha256 ON public.dim_origen_documental(hash_sha256);

CREATE TABLE public.dim_categoria_financiera (
    id_categoria SERIAL PRIMARY KEY,
    nombre_categoria VARCHAR(200) NOT NULL UNIQUE,
    tipo VARCHAR(50), -- 'INGRESO', 'EGRESO', 'RENTABILIDAD', 'EBITDA'
    id_cat_categoria_fin INT REFERENCES public.cat_categoria_financiera(id_categoria_fin) ON DELETE SET NULL
);

CREATE TABLE public.dim_meta (
    id_meta SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL,
    id_tiempo INT REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    monto_meta NUMERIC(14, 2),
    tipo_programa VARCHAR(50)
);
CREATE INDEX idx_dim_meta_tiempo ON public.dim_meta(id_tiempo);
CREATE INDEX idx_dim_meta_cat ON public.dim_meta(categoria);

-- ==========================================
-- 3. AUDITORÍA Y CALIDAD DE DATOS NLP
-- ==========================================
CREATE TABLE public.log_auditoria_nlp (
    id_log SERIAL PRIMARY KEY,
    texto_original VARCHAR(500) NOT NULL,
    prediccion_beto VARCHAR(200),
    confianza_ia NUMERIC(5, 4),
    correccion_humana VARCHAR(200) NOT NULL,
    usuario_auditor INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 4. TABLAS DE HECHOS (FACTS)
-- ==========================================

-- A. Rendimiento Académico
CREATE TABLE public.fact_rendimiento_academico (
    id_hecho_aca SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE CASCADE,
    id_docente INTEGER REFERENCES public.dim_docente(id_docente) ON DELETE SET NULL,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    id_usuario_carga INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    nota_final NUMERIC(5, 2),
    asistencia_pct NUMERIC(5, 2),
    incumplimiento_actividades_pct NUMERIC(5, 2) DEFAULT 0.00,
    nivel_confianza_ia NUMERIC(5, 4),
    requiere_revision BOOLEAN DEFAULT FALSE,
    fk_estado VARCHAR(1) DEFAULT 'A',
    estado_academico VARCHAR(50),
    estado_tutoria VARCHAR(50),
    estado_arca VARCHAR(50),
    tipo_alerta VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- B. Finanzas y Cobranza
CREATE TABLE public.fact_situacion_financiera (
    id_hecho_fin SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE CASCADE,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE SET NULL,
    id_categoria_fin INTEGER REFERENCES public.dim_categoria_financiera(id_categoria) ON DELETE SET NULL,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    concepto VARCHAR(150),
    monto_deuda NUMERIC(12, 2) DEFAULT 0.00,
    monto_pagado NUMERIC(12, 2) DEFAULT 0.00,
    cuotas_impagas INTEGER DEFAULT 0,
    estado_cartera VARCHAR(20),
    tipo_alerta VARCHAR(30) DEFAULT 'NORMAL',
    nivel_confianza_ia NUMERIC(5, 4) DEFAULT 1.0000,
    requiere_revision BOOLEAN DEFAULT FALSE,
    fk_estado VARCHAR(1) DEFAULT 'A',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.fact_cobranzas_proyectadas (
    id_hecho_cobro SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    monto_esperado NUMERIC(10, 2),
    estado_pago VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- C. Evaluaciones NPS Docentes
CREATE TABLE public.fact_evaluacion_docente (
    id_hecho_eval SERIAL PRIMARY KEY,
    id_docente INTEGER REFERENCES public.dim_docente(id_docente) ON DELETE CASCADE,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE SET NULL,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    pregunta_bloque VARCHAR(500),
    puntuacion NUMERIC(4, 2),
    comentario VARCHAR(1000),
    tipo_pregunta VARCHAR(20),
    escala_max INTEGER,
    clave_respuesta VARCHAR(64) UNIQUE
);

-- D. Marketing y Embudo Comercial
CREATE TABLE public.fact_marketing (
    id_hecho_mkt SERIAL PRIMARY KEY,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    leads INTEGER DEFAULT 0,
    reservas INTEGER DEFAULT 0,
    inscritos INTEGER DEFAULT 0,
    costo_programa NUMERIC(12, 2)
);

-- E. Rentabilidad General / OKR's Ejecutivos
CREATE TABLE public.fact_rentabilidad (
    id_hecho_rent SERIAL PRIMARY KEY,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    id_categoria INTEGER REFERENCES public.dim_categoria_financiera(id_categoria) ON DELETE CASCADE,
    monto_ejecutado NUMERIC(14, 2),
    monto_meta NUMERIC(14, 2)
);

-- E2. Costos por programa (grano: un POS; fact_rentabilidad es mensual por categoría)
CREATE TABLE public.fact_costo_programa (
    id_hecho_costo SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL UNIQUE REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    egreso_anterior NUMERIC(14, 2),
    egreso_real NUMERIC(14, 2),
    ingreso NUMERIC(14, 2),
    rentabilidad NUMERIC(14, 2),
    requiere_revision BOOLEAN DEFAULT FALSE,
    motivo_revision VARCHAR(300),
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- E3. Docente(s) de cada módulo (hoja MODULOS)
CREATE TABLE IF NOT EXISTS public.bridge_modulo_docente (
    id_asignacion SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_docente INTEGER NOT NULL REFERENCES public.dim_docente(id_docente) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    tipo_docente VARCHAR(30),
    grado_academico VARCHAR(50),
    horas_modulo NUMERIC(6, 2),
    pago_docente NUMERIC(12, 2),
    fecha_inicio DATE,
    fecha_fin DATE,
    CONSTRAINT uq_bridge_modulo_docente UNIQUE (id_modulo, id_docente)
);
CREATE INDEX IF NOT EXISTS idx_bridge_mod_doc_modulo ON public.bridge_modulo_docente (id_modulo);
CREATE INDEX IF NOT EXISTS idx_bridge_mod_doc_docente ON public.bridge_modulo_docente (id_docente);

-- E4. Convenios con instituciones (techos)
CREATE TABLE IF NOT EXISTS public.fact_techo_convenio (
    id_hecho_techo SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE SET NULL,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    clave_convenio VARCHAR(40) NOT NULL UNIQUE,
    institucion VARCHAR(200) NOT NULL,
    id_convenio_catalogo INTEGER,
    monto_convenio NUMERIC(14, 2),
    n_inscritos INTEGER,
    gestion INTEGER,
    fecha_inicio DATE,
    fecha_fin DATE,
    requiere_revision BOOLEAN DEFAULT FALSE,
    motivo_revision VARCHAR(300),
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fact_techo_modulo ON public.fact_techo_convenio (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_techo_institucion ON public.fact_techo_convenio (institucion);

-- F. Pronósticos de Negocio (Forecasting)
CREATE TABLE public.fact_forecast (
    id_forecast SERIAL PRIMARY KEY,
    caso_uso VARCHAR(50) NOT NULL,
    id_tiempo INT REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    valor_forecast NUMERIC(14, 2) NOT NULL,
    ic_lower NUMERIC(14, 2),
    ic_upper NUMERIC(14, 2),
    metodo VARCHAR(30) NOT NULL DEFAULT 'HoltWinters',
    horizonte_meses INT NOT NULL,
    generado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_forecast_caso_tiempo UNIQUE (caso_uso, id_tiempo)
);
CREATE INDEX idx_fact_forecast_caso ON public.fact_forecast(caso_uso);

-- ==========================================
-- 5. TABLAS DE STAGING Y TRAZABILIDAD (DATAOPS)
-- ==========================================
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
CREATE INDEX IF NOT EXISTS idx_staging_doc_id ON public.staging_registros_crudos(id_documento);

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
CREATE INDEX IF NOT EXISTS idx_stg_entidad_doc ON public.stg_entidad_no_resuelta(id_documento);

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

CREATE TABLE IF NOT EXISTS public.log_pipeline_ingesta (
    id SERIAL PRIMARY KEY,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
    etapa VARCHAR(50) NOT NULL,
    nivel VARCHAR(10) NOT NULL,
    modulo VARCHAR(100),
    mensaje TEXT NOT NULL,
    tiempo_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_log_pipeline_doc ON public.log_pipeline_ingesta(id_documento);

-- ==========================================
-- 6. HABILITAR SEGURIDAD (RLS)
-- ==========================================
DO $$ 
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $$;

-- ==========================================
-- 7. POLÍTICAS DE ACCESO
-- ==========================================

-- A. LECTURA (Todos los usuarios autenticados pueden leer todo para los dashboards)
DO $$ 
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('CREATE POLICY "Lectura_Global" ON public.%I FOR SELECT USING (true)', r.tablename);
  END LOOP;
END $$;

-- B. ESCRITURA (ADMIN tiene acceso total a todas las tablas)
DO $$ 
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('CREATE POLICY "Admin_All_Access" ON public.%I FOR ALL USING (current_setting(''request.jwt.claims'', true)::json->>''role'' = ''admin'')', r.tablename);
  END LOOP;
END $$;

-- C. ESCRITURA (Coordinador Académico: Solo a Dimensiones, Académico y NPS)
CREATE POLICY "Coord_Inserts_Aca" ON public.fact_rendimiento_academico FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'coordinador_academico');
CREATE POLICY "Coord_Inserts_NPS" ON public.fact_evaluacion_docente FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'coordinador_academico');

-- D. ESCRITURA (Analista de Datos / Marketing: Solo Finanzas, Marketing y Rentabilidad)
CREATE POLICY "Analista_Inserts_Fin" ON public.fact_situacion_financiera FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'analista_datos_marketing');
CREATE POLICY "Analista_Inserts_Cob" ON public.fact_cobranzas_proyectadas FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'analista_datos_marketing');
CREATE POLICY "Analista_Inserts_Mkt" ON public.fact_marketing FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'analista_datos_marketing');
CREATE POLICY "Analista_Inserts_Rent" ON public.fact_rentabilidad FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'analista_datos_marketing');

-- (Para que los roles puedan crear estudiantes o docentes si no existen, les damos permisos en dimensiones)
CREATE POLICY "Coord_Insert_Dims" ON public.dim_estudiante FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'coordinador_academico');
CREATE POLICY "Analista_Insert_Dims" ON public.dim_estudiante FOR INSERT WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'analista_datos_marketing');

-- ==========================================
-- 8. RESTRICCIONES DE UNICIDAD (DEDUPLICACIÓN AUTOMÁTICA EN INGESTA)
-- ==========================================
ALTER TABLE public.fact_marketing ADD CONSTRAINT uq_fact_marketing_modulo_tiempo UNIQUE (id_modulo, id_tiempo);
ALTER TABLE public.fact_rentabilidad ADD CONSTRAINT uq_fact_rentabilidad_categoria_tiempo UNIQUE (id_categoria, id_tiempo);
ALTER TABLE public.fact_rendimiento_academico ADD CONSTRAINT uq_fact_rendimiento_estudiante_modulo UNIQUE (id_estudiante, id_modulo);
CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_fin_est_mod_tiempo ON public.fact_situacion_financiera (id_estudiante, COALESCE(id_modulo, 0), id_tiempo);
ALTER TABLE public.fact_cobranzas_proyectadas ADD CONSTRAINT uq_fact_cobranzas_proyectadas_estudiante_tiempo UNIQUE (id_estudiante, id_tiempo);

-- ==========================================
-- 9. ÍNDICES DE CONSULTA (migraciones 001, V005-V010 y modelos)
-- Las claves primarias y UNIQUE ya crean su índice: no se repiten (uq_fact_aca_est_mod duplicaba
-- uq_fact_rendimiento_estudiante_modulo; ver backend/scripts/migrations/005_alinear_esquema_con_ddl.sql).
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_fact_rend_estudiante ON public.fact_rendimiento_academico (id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_rend_modulo ON public.fact_rendimiento_academico (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_rend_docente ON public.fact_rendimiento_academico (id_docente);
CREATE INDEX IF NOT EXISTS idx_fact_rend_tiempo ON public.fact_rendimiento_academico (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_rend_documento ON public.fact_rendimiento_academico (id_documento);
CREATE INDEX IF NOT EXISTS idx_fact_rendimiento_fk_estado ON public.fact_rendimiento_academico (fk_estado);
CREATE INDEX IF NOT EXISTS idx_fact_fin_estudiante ON public.fact_situacion_financiera (id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_fin_modulo ON public.fact_situacion_financiera (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_fin_tiempo ON public.fact_situacion_financiera (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_fin_documento ON public.fact_situacion_financiera (id_documento);
CREATE INDEX IF NOT EXISTS idx_fact_fin_estado_cartera ON public.fact_situacion_financiera (estado_cartera);
CREATE INDEX IF NOT EXISTS idx_fact_financiera_fk_estado ON public.fact_situacion_financiera (fk_estado);
CREATE INDEX IF NOT EXISTS idx_fact_financiera_revision ON public.fact_situacion_financiera (requiere_revision);
CREATE INDEX IF NOT EXISTS idx_fact_fin_mora_estudiante ON public.fact_situacion_financiera (id_estudiante) WHERE cuotas_impagas >= 2;
CREATE INDEX IF NOT EXISTS idx_fact_mkt_tiempo ON public.fact_marketing (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_rent_tiempo ON public.fact_rentabilidad (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_cobproy_tiempo ON public.fact_cobranzas_proyectadas (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_estudiante ON public.fact_evaluacion_docente (id_estudiante);
CREATE INDEX IF NOT EXISTS idx_fact_eval_modulo ON public.fact_evaluacion_docente (id_modulo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_tiempo ON public.fact_evaluacion_docente (id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fact_eval_docente ON public.fact_evaluacion_docente (id_docente);
CREATE INDEX IF NOT EXISTS idx_dim_tiempo_gestion ON public.dim_tiempo (gestion);
CREATE INDEX IF NOT EXISTS ix_fact_forecast_id_tiempo ON public.fact_forecast (id_tiempo);
CREATE INDEX IF NOT EXISTS ix_log_inconsistencias_tipo_regla ON public.log_inconsistencias (tipo_regla);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON public.notifications (user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_stg_entidad_resuelto ON public.stg_entidad_no_resuelta (resuelto, estado_resolucion);
CREATE INDEX IF NOT EXISTS idx_stg_entidad_registro ON public.stg_entidad_no_resuelta (registro_origen_id);
CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_estado ON public.stg_entidad_no_resuelta (resuelto);
CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_tipo ON public.stg_entidad_no_resuelta (tipo_entidad);
CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_motivo ON public.stg_entidad_no_resuelta (motivo);
CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_estado_res ON public.stg_entidad_no_resuelta (estado_resolucion);
CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_lock ON public.stg_entidad_no_resuelta (lock_usuario_id, lock_expira);

-- Indices covering para agregaciones rapidas de KPIs y Alertas:
CREATE INDEX IF NOT EXISTS idx_fact_rend_tiempo_modulo_cov ON public.fact_rendimiento_academico (id_tiempo, id_modulo) INCLUDE (id_estudiante, nota_final, asistencia_pct, incumplimiento_actividades_pct, nivel_confianza_ia, requiere_revision);
CREATE INDEX IF NOT EXISTS idx_fact_fin_tiempo_modulo_cov ON public.fact_situacion_financiera (id_tiempo, id_modulo) INCLUDE (id_estudiante, monto_pagado, monto_deuda, cuotas_impagas, estado_cartera);
CREATE INDEX IF NOT EXISTS idx_log_ingesta_etapa_id_desc ON public.log_pipeline_ingesta (etapa, id DESC);
