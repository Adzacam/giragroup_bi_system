-- ============================================================================
-- Migración Versionada: 005_alinear_esquema_con_ddl.sql
-- Propósito:
--   Alinear una base creada por versiones anteriores (create_all de SQLAlchemy, migraciones 002/003,
--   respaldos B0/B1) con el DDL del repositorio (db/schema.sql) en las 26 tablas que este define:
--   1. Índices duplicados: uq_fact_aca_est_mod repite la restricción uq_fact_rendimiento_estudiante_modulo,
--      y los ix_*_id de SQLAlchemy repiten la clave primaria.
--   2. dim_tiempo: clave inteligente YYYYMMDD sin secuencia, sin DEFAULT de relleno (gestión 2026, mes 5,
--      semestre 1), todas las columnas NOT NULL y fecha UNIQUE.
--   3. DEFAULT, tipos y NOT NULL del DDL; FK con su ON DELETE; UNIQUE de dim_categoria_financiera.
--   4. RLS y políticas Lectura_Global / Admin_All_Access del DDL (giragroup_user es superusuario: no le aplican).
-- Idempotente: se puede volver a aplicar sobre una base ya alineada.
-- ============================================================================

BEGIN;

-- 1. Índices duplicados ------------------------------------------------------
DROP INDEX IF EXISTS public.uq_fact_aca_est_mod;
DROP INDEX IF EXISTS public.ix_dim_meta_id_meta;
DROP INDEX IF EXISTS public.ix_fact_forecast_id_forecast;
DROP INDEX IF EXISTS public.ix_log_inconsistencias_id_inconsistencia;
DROP INDEX IF EXISTS public.ix_log_pipeline_ingesta_id;
DROP INDEX IF EXISTS public.ix_lote_id_lote;
DROP INDEX IF EXISTS public.ix_staging_registros_crudos_id;
DROP INDEX IF EXISTS public.ix_stg_entidad_no_resuelta_id_staging;

-- 2. dim_tiempo ----------------------------------------------------------------
-- Filas sin fecha: la clave es YYYYMMDD
UPDATE public.dim_tiempo SET fecha = to_date(id_tiempo::text, 'YYYYMMDD')
WHERE fecha IS NULL AND id_tiempo BETWEEN 19000101 AND 21001231;
-- Atributos derivados de la fecha (mismos valores que DWLoaderService.resolver_o_crear_tiempo)
UPDATE public.dim_tiempo SET
    gestion       = EXTRACT(YEAR FROM fecha)::int,
    mes           = EXTRACT(MONTH FROM fecha)::int,
    semestre      = CASE WHEN EXTRACT(MONTH FROM fecha) <= 6 THEN 1 ELSE 2 END,
    trimestre     = EXTRACT(QUARTER FROM fecha)::int,
    nombre_mes    = (ARRAY['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre',
                           'Octubre','Noviembre','Diciembre'])[EXTRACT(MONTH FROM fecha)::int],
    semana_iso    = EXTRACT(WEEK FROM fecha)::int,
    dia_mes       = EXTRACT(DAY FROM fecha)::int,
    dia_semana    = EXTRACT(ISODOW FROM fecha)::int,
    nombre_dia    = (ARRAY['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'])[EXTRACT(ISODOW FROM fecha)::int],
    es_fin_semana = EXTRACT(ISODOW FROM fecha) >= 6,
    periodo_mes   = to_char(fecha, 'YYYY-MM')
WHERE fecha IS NOT NULL AND (
    gestion IS NULL OR mes IS NULL OR semestre IS NULL OR trimestre IS NULL OR nombre_mes IS NULL
    OR semana_iso IS NULL OR dia_mes IS NULL OR dia_semana IS NULL OR nombre_dia IS NULL
    OR es_fin_semana IS NULL OR periodo_mes IS NULL OR length(periodo_mes) > 7
);

ALTER TABLE public.dim_tiempo
    ALTER COLUMN id_tiempo DROP DEFAULT,
    ALTER COLUMN gestion DROP DEFAULT,
    ALTER COLUMN mes DROP DEFAULT,
    ALTER COLUMN semestre DROP DEFAULT,
    ALTER COLUMN nombre_mes TYPE VARCHAR(20),
    ALTER COLUMN periodo_mes TYPE VARCHAR(7),
    ALTER COLUMN fecha SET NOT NULL,
    ALTER COLUMN gestion SET NOT NULL,
    ALTER COLUMN semestre SET NOT NULL,
    ALTER COLUMN trimestre SET NOT NULL,
    ALTER COLUMN mes SET NOT NULL,
    ALTER COLUMN nombre_mes SET NOT NULL,
    ALTER COLUMN semana_iso SET NOT NULL,
    ALTER COLUMN dia_mes SET NOT NULL,
    ALTER COLUMN dia_semana SET NOT NULL,
    ALTER COLUMN nombre_dia SET NOT NULL,
    ALTER COLUMN es_fin_semana SET NOT NULL,
    ALTER COLUMN periodo_mes SET NOT NULL;
DROP SEQUENCE IF EXISTS public.dim_tiempo_id_tiempo_seq;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.dim_tiempo'::regclass AND contype = 'u'
                     AND pg_get_constraintdef(oid) = 'UNIQUE (fecha)') THEN
        ALTER TABLE public.dim_tiempo ADD CONSTRAINT dim_tiempo_fecha_key UNIQUE (fecha);
    END IF;
END $$;
DROP INDEX IF EXISTS public.idx_dim_tiempo_fecha;  -- lo cubre dim_tiempo_fecha_key
CREATE INDEX IF NOT EXISTS idx_dim_tiempo_periodo ON public.dim_tiempo (periodo_mes);

-- 3. DEFAULT, tipos y NOT NULL ---------------------------------------------------
ALTER TABLE public.dim_modulo ALTER COLUMN nombre_institucion SET DEFAULT 'GiraGroup Posgrado';
ALTER TABLE public.fact_forecast
    ALTER COLUMN generado_en SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN metodo SET DEFAULT 'HoltWinters';
ALTER TABLE public.fact_situacion_financiera
    ALTER COLUMN monto_deuda TYPE NUMERIC(12, 2),
    ALTER COLUMN monto_deuda SET DEFAULT 0.00,
    ALTER COLUMN cuotas_impagas SET DEFAULT 0,
    ALTER COLUMN nivel_confianza_ia SET DEFAULT 1.0000;
ALTER TABLE public.log_inconsistencias
    ALTER COLUMN detectado_en SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN estado_resolucion SET DEFAULT 'BLOQUEADO',
    ALTER COLUMN severidad SET DEFAULT 'ALTA';
ALTER TABLE public.log_pipeline_ingesta
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb;
ALTER TABLE public.lote
    ALTER COLUMN creado_en SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN estado SET DEFAULT 'PROCESADO',
    ALTER COLUMN total_archivos SET DEFAULT 0;
ALTER TABLE public.staging_registros_crudos
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN es_ruido SET DEFAULT FALSE;
ALTER TABLE public.stg_entidad_no_resuelta
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN fk_estado SET DEFAULT 'C',
    ALTER COLUMN resuelto SET DEFAULT FALSE,
    ALTER COLUMN tipo_entidad TYPE VARCHAR(50);
-- Las fechas guardadas sin zona son hora del servidor (UTC en el contenedor)
ALTER TABLE public.users
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN email SET NOT NULL;

-- FK con el ON DELETE del DDL (y de los modelos, para las que apuntan a catálogos fuera de schema.sql)
DO $$
DECLARE
    fk record;
    c record;
BEGIN
    FOR fk IN SELECT * FROM (VALUES
        ('dim_categoria_financiera', 'id_cat_categoria_fin', 'cat_categoria_financiera', 'id_categoria_fin', 'SET NULL'),
        ('dim_estudiante',           'fusionado_en',         'dim_estudiante',           'id_estudiante',    'SET NULL'),
        ('dim_estudiante',           'id_institucion',       'cat_institucion',          'id_institucion',   'SET NULL'),
        ('fact_situacion_financiera','id_modulo',            'dim_modulo',               'id_modulo',        'SET NULL'),
        ('dim_docente',              'id_cat_docente',       'cat_docente',              'id_docente',       'SET NULL'),
        ('dim_modulo',               'id_cat_modulo',        'cat_modulo',               'id_modulo',        'SET NULL'),
        ('stg_entidad_no_resuelta',  'registro_origen_id',   'staging_registros_crudos', 'id',               'CASCADE')
    ) AS t(tabla, columna, ref_tabla, ref_columna, accion)
    LOOP
        IF to_regclass('public.' || fk.ref_tabla) IS NULL THEN
            CONTINUE;
        END IF;
        FOR c IN SELECT conname FROM pg_constraint
                 WHERE conrelid = ('public.' || fk.tabla)::regclass AND contype = 'f'
                   AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                                       WHERE attrelid = ('public.' || fk.tabla)::regclass AND attname = fk.columna)]
        LOOP
            EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', fk.tabla, c.conname);
        END LOOP;
        -- Referencias huérfanas: NULL (no se pierden filas al crear la FK)
        EXECUTE format('UPDATE public.%I t SET %I = NULL WHERE %I IS NOT NULL AND NOT EXISTS '
                       '(SELECT 1 FROM public.%I r WHERE r.%I = t.%I)',
                       fk.tabla, fk.columna, fk.columna, fk.ref_tabla, fk.ref_columna, fk.columna);
        EXECUTE format('ALTER TABLE public.%I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES public.%I (%I) ON DELETE %s',
                       fk.tabla, fk.tabla || '_' || fk.columna || '_fkey', fk.columna, fk.ref_tabla, fk.ref_columna, fk.accion);
    END LOOP;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.dim_categoria_financiera'::regclass AND contype = 'u'
                     AND pg_get_constraintdef(oid) = 'UNIQUE (nombre_categoria)') THEN
        ALTER TABLE public.dim_categoria_financiera
            ADD CONSTRAINT dim_categoria_financiera_nombre_categoria_key UNIQUE (nombre_categoria);
    END IF;
END $$;

-- Índices de las migraciones 001, V005–V010 y de los modelos (también declarados en db/schema.sql)
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

-- 4. RLS y políticas del DDL -----------------------------------------------------
DO $$
DECLARE
    t text;
    p record;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'notifications', 'lote', 'cat_institucion', 'cat_categoria_financiera', 'cat_docente', 'cat_modulo', 'dim_tiempo',
        'dim_estudiante', 'dim_docente', 'dim_modulo', 'dim_origen_documental', 'dim_categoria_financiera',
        'dim_meta', 'log_auditoria_nlp', 'fact_rendimiento_academico', 'fact_situacion_financiera',
        'fact_cobranzas_proyectadas', 'fact_marketing', 'fact_rentabilidad', 'fact_evaluacion_docente',
        'fact_forecast', 'staging_registros_crudos', 'stg_entidad_no_resuelta', 'log_inconsistencias',
        'log_pipeline_ingesta']
    LOOP
        IF to_regclass('public.' || t) IS NULL THEN
            CONTINUE;
        END IF;
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        -- Políticas permisivas de 002/003 (USING true) que el DDL no declara
        FOR p IN SELECT policyname FROM pg_policies
                 WHERE schemaname = 'public' AND tablename = t AND policyname NOT IN (
                     'Lectura_Global', 'Admin_All_Access', 'Coord_Inserts_Aca', 'Coord_Inserts_NPS',
                     'Analista_Inserts_Fin', 'Analista_Inserts_Cob', 'Analista_Inserts_Mkt',
                     'Analista_Inserts_Rent', 'Coord_Insert_Dims', 'Analista_Insert_Dims')
        LOOP
            EXECUTE format('DROP POLICY %I ON public.%I', p.policyname, t);
        END LOOP;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = t AND policyname = 'Lectura_Global') THEN
            EXECUTE format('CREATE POLICY "Lectura_Global" ON public.%I FOR SELECT USING (true)', t);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = t AND policyname = 'Admin_All_Access') THEN
            EXECUTE format('CREATE POLICY "Admin_All_Access" ON public.%I FOR ALL USING (current_setting(''request.jwt.claims'', true)::json->>''role'' = ''admin'')', t);
        END IF;
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE public.schema_migrations ALTER COLUMN version TYPE VARCHAR(255);  -- 001 la creó con VARCHAR(150)
INSERT INTO public.schema_migrations (version, applied_at)
VALUES ('005_alinear_esquema_con_ddl.sql', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

COMMIT;
