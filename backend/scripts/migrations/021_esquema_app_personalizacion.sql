-- 021_esquema_app_personalizacion.sql
-- Decisiones D3, D4, D6 (REESTRUCTURACION_VISTA_V2): esquema `app` separado de `public` y `bi`
-- para KPIs personalizados (KPP-nn) y gráficas personalizadas sin alterar el invariante 51/10/23.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.medida_catalogo (
    codigo VARCHAR(40) PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    perspectiva VARCHAR(30) NOT NULL,
    origen_schema VARCHAR(20) NOT NULL,
    origen_tabla VARCHAR(80) NOT NULL,
    columna_medida VARCHAR(80) NOT NULL,
    agregaciones_permitidas TEXT[] NOT NULL,
    dimensiones_permitidas JSONB NOT NULL DEFAULT '[]'::jsonb,
    unidad VARCHAR(12) NOT NULL DEFAULT 'CANT',
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS app.kpi_personalizado (
    codigo VARCHAR(20) PRIMARY KEY,
    perspectiva VARCHAR(30) NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(300),
    medida_codigo VARCHAR(40) NOT NULL REFERENCES app.medida_catalogo(codigo),
    agregacion VARCHAR(20) NOT NULL DEFAULT 'SUM',
    unidad VARCHAR(12) NOT NULL DEFAULT 'CANT',
    sentido VARCHAR(5) NOT NULL DEFAULT 'MAX',
    meta NUMERIC(14, 2),
    umbral_verde NUMERIC(14, 2),
    umbral_ambar NUMERIC(14, 2),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    creado_por VARCHAR(80) NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_por VARCHAR(80),
    actualizado_en TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS app.grafico_personalizado (
    id SERIAL PRIMARY KEY,
    perspectiva VARCHAR(30) NOT NULL,
    titulo VARCHAR(120) NOT NULL,
    medida_codigo VARCHAR(40) NOT NULL REFERENCES app.medida_catalogo(codigo),
    dimension_codigo VARCHAR(60) NOT NULL,
    agregacion VARCHAR(20) NOT NULL DEFAULT 'SUM',
    tipo_grafico VARCHAR(20) NOT NULL DEFAULT 'bar',
    orden INTEGER NOT NULL DEFAULT 10,
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    creado_por VARCHAR(80) NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_por VARCHAR(80),
    actualizado_en TIMESTAMPTZ
);

-- Semilla de medidas en lista blanca (cero PII: dim_estudiante queda fuera)
INSERT INTO app.medida_catalogo
    (codigo, nombre, perspectiva, origen_schema, origen_tabla, columna_medida, agregaciones_permitidas, dimensiones_permitidas, unidad, descripcion)
VALUES
    ('MED_EJECUTADO_MES', 'Recaudación ejecutada mensual (Bs)', 'FINANCIERA', 'bi', 'vw_metas_mensual', 'ejecutado',
     ARRAY['SUM', 'AVG', 'MAX', 'MIN'],
     '[{"codigo":"nombre_mes","label":"Mes","expr":"nombre_mes"},{"codigo":"categoria","label":"Categoría","expr":"categoria"},{"codigo":"gestion","label":"Gestión","expr":"gestion::text"}]'::jsonb,
     'BS', 'Ingresos ejecutados mensuales desde bi.vw_metas_mensual.'),
    ('MED_META_MES', 'Meta mensual presupuestada (Bs)', 'FINANCIERA', 'bi', 'vw_metas_mensual', 'meta',
     ARRAY['SUM', 'AVG', 'MAX', 'MIN'],
     '[{"codigo":"nombre_mes","label":"Mes","expr":"nombre_mes"},{"codigo":"categoria","label":"Categoría","expr":"categoria"},{"codigo":"gestion","label":"Gestión","expr":"gestion::text"}]'::jsonb,
     'BS', 'Metas mensuales desde bi.vw_metas_mensual.'),
    ('MED_DEUDA_CARTERA', 'Deuda de cartera (Bs)', 'FINANCIERA', 'bi', 'vw_cartera_estado', 'deuda_bs',
     ARRAY['SUM', 'AVG', 'MAX'],
     '[{"codigo":"estado_cartera","label":"Estado de cartera","expr":"estado_cartera"},{"codigo":"gestion","label":"Gestión","expr":"gestion::text"}]'::jsonb,
     'BS', 'Saldo pendiente por estado de cartera desde bi.vw_cartera_estado.'),
    ('MED_INSCRIPCIONES', 'Cantidad de inscripciones', 'CLIENTES', 'public', 'fact_inscripcion', 'id_inscripcion',
     ARRAY['COUNT', 'COUNT_DISTINCT'],
     '[{"codigo":"programa","label":"Programa","join":"JOIN public.dim_programa dp ON dp.id_programa = base.id_programa","expr":"dp.nombre"},{"codigo":"modalidad","label":"Modalidad","join":"JOIN public.dim_modalidad dm ON dm.id_modalidad = base.id_modalidad","expr":"dm.nombre"},{"codigo":"gestion","label":"Gestión","join":"JOIN public.dim_tiempo dt ON dt.id_tiempo = base.id_tiempo","expr":"dt.anio::text"}]'::jsonb,
     'CANT', 'Inscripciones agregadas desde fact_inscripcion sin PII.'),
    ('MED_CAPTACION_INTERESADOS', 'Interesados por fuente de captación', 'CLIENTES', 'public', 'fact_captacion_marketing', 'interesados',
     ARRAY['SUM', 'AVG', 'COUNT'],
     '[{"codigo":"fuente","label":"Fuente de captación","join":"LEFT JOIN public.dim_fuente_captacion df ON df.id_fuente = base.id_fuente","expr":"COALESCE(df.nombre_fuente, ''Sin fuente'')"},{"codigo":"gestion","label":"Gestión","join":"JOIN public.dim_tiempo dt ON dt.id_tiempo = base.id_tiempo","expr":"dt.anio::text"}]'::jsonb,
     'CANT', 'Interesados captados desde fact_captacion_marketing.'),
    ('MED_DATAOPS_REGISTROS', 'Registros procesados DataOps', 'PROCESOS_INTERNOS', 'bi', 'vw_dataops_documento', 'registros',
     ARRAY['SUM', 'AVG', 'COUNT'],
     '[{"codigo":"tipo_fuente","label":"Tipo de fuente","expr":"tipo_fuente"},{"codigo":"periodo","label":"Periodo","expr":"periodo"}]'::jsonb,
     'CANT', 'Volumen de registros documentales desde bi.vw_dataops_documento.'),
    ('MED_DATAOPS_CONFIANZA', 'Confianza media de extracción (%)', 'PROCESOS_INTERNOS', 'bi', 'vw_dataops_documento', 'confianza_media_pct',
     ARRAY['AVG', 'MIN', 'MAX'],
     '[{"codigo":"tipo_fuente","label":"Tipo de fuente","expr":"tipo_fuente"}]'::jsonb,
     'PCT', 'Índice de confianza media BETO desde bi.vw_dataops_documento.'),
    ('MED_RIESGO_NIVEL', 'Estudiantes en alerta temprana', 'APRENDIZAJE', 'bi', 'vw_riesgo_estudiante', 'id_estudiante',
     ARRAY['COUNT', 'COUNT_DISTINCT'],
     '[{"codigo":"nivel_prioridad","label":"Nivel de prioridad","expr":"nivel_prioridad"},{"codigo":"gestion","label":"Gestión","expr":"gestion::text"}]'::jsonb,
     'CANT', 'Conteo agregado por nivel de riesgo desde bi.vw_riesgo_estudiante (grupos < 5 ocultos).')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.schema_migrations (version)
VALUES ('021_esquema_app_personalizacion.sql')
ON CONFLICT (version) DO NOTHING;
