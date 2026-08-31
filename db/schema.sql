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
-- 1. TABLA DE USUARIOS / SISTEMA
-- ==========================================
CREATE TABLE public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL DEFAULT 'sistema',
    hashed_password VARCHAR(255) NOT NULL DEFAULT '$placeholder$',
    role VARCHAR(50) DEFAULT 'admin',
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
CREATE INDEX idx_dim_tiempo_fecha ON public.dim_tiempo(fecha);
CREATE INDEX idx_dim_tiempo_periodo ON public.dim_tiempo(periodo_mes);

CREATE TABLE public.dim_estudiante (
    id_estudiante SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    codigo_estudiante VARCHAR(50),
    genero VARCHAR(20),
    ciudad VARCHAR(100),
    nivel_academico VARCHAR(100),
    edad INTEGER,
    ocupacion VARCHAR(100),
    estado_civil VARCHAR(50)
);
CREATE INDEX idx_dim_est_id ON public.dim_estudiante(id_estudiante);

CREATE TABLE public.dim_docente (
    id_docente SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL DEFAULT 'Docente Generico',
    area_especialidad VARCHAR(200) DEFAULT 'Generico'
);

CREATE TABLE public.dim_modulo (
    id_modulo SERIAL PRIMARY KEY,
    nombre_modulo VARCHAR(200) NOT NULL DEFAULT 'Modulo Generico',
    nombre_institucion VARCHAR(200) NOT NULL DEFAULT 'GiraGroup',
    programa VARCHAR(200) DEFAULT 'General',
    pos_code VARCHAR(50)
);

CREATE TABLE public.dim_origen_documental (
    id_documento SERIAL PRIMARY KEY,
    tipo_documento VARCHAR(10) DEFAULT 'SHEET',
    nombre_archivo VARCHAR(500) DEFAULT 'archivo_generico',
    fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.dim_categoria_financiera (
    id_categoria SERIAL PRIMARY KEY,
    nombre_categoria VARCHAR(200) NOT NULL UNIQUE,
    tipo VARCHAR(50) -- 'INGRESO', 'EGRESO', 'RENTABILIDAD', 'EBITDA'
);

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
CREATE INDEX idx_log_auditoria_nlp_id ON public.log_auditoria_nlp(id_log);

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
    estado_academico VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_fact_rendimiento_aca_id ON public.fact_rendimiento_academico(id_hecho_aca);

-- B. Finanzas y Cobranza
CREATE TABLE public.fact_situacion_financiera (
    id_hecho_fin SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE CASCADE,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    monto_deuda NUMERIC(10, 2),
    cuotas_impagas INTEGER,
    estado_cartera VARCHAR(20),
    tipo_alerta VARCHAR(20),
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
CREATE INDEX idx_fact_cobro_id ON public.fact_cobranzas_proyectadas(id_hecho_cobro);

-- C. Evaluaciones NPS Docentes
CREATE TABLE public.fact_evaluacion_docente (
    id_hecho_eval SERIAL PRIMARY KEY,
    id_docente INTEGER REFERENCES public.dim_docente(id_docente) ON DELETE CASCADE,
    id_modulo INTEGER REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_estudiante INTEGER REFERENCES public.dim_estudiante(id_estudiante) ON DELETE SET NULL,
    id_tiempo INTEGER REFERENCES public.dim_tiempo(id_tiempo) ON DELETE CASCADE,
    pregunta_bloque VARCHAR(500),
    puntuacion NUMERIC(4, 2),
    comentario VARCHAR(1000)
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

-- ==========================================
-- 5. HABILITAR SEGURIDAD (RLS)
-- ==========================================
DO $$ 
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $$;

-- ==========================================
-- 6. POLÍTICAS DE ACCESO
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
-- 7. RESTRICCIONES DE UNICIDAD (DEDUPLICACIÓN AUTOMÁTICA EN INGESTA)
-- ==========================================
ALTER TABLE public.fact_marketing ADD CONSTRAINT uq_fact_marketing_modulo_tiempo UNIQUE (id_modulo, id_tiempo);
ALTER TABLE public.fact_rentabilidad ADD CONSTRAINT uq_fact_rentabilidad_categoria_tiempo UNIQUE (id_categoria, id_tiempo);
ALTER TABLE public.fact_rendimiento_academico ADD CONSTRAINT uq_fact_rendimiento_estudiante_modulo UNIQUE (id_estudiante, id_modulo);
ALTER TABLE public.fact_situacion_financiera ADD CONSTRAINT uq_fact_situacion_financiera_estudiante_tiempo UNIQUE (id_estudiante, id_tiempo);
ALTER TABLE public.fact_cobranzas_proyectadas ADD CONSTRAINT uq_fact_cobranzas_proyectadas_estudiante_tiempo UNIQUE (id_estudiante, id_tiempo);