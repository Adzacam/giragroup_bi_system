-- Catálogo de reglas configurables de validación de relaciones (BA-L6) en giragroup_catalog_db
CREATE TABLE IF NOT EXISTS public.cat_regla_relacion (
    id_regla SERIAL PRIMARY KEY,
    codigo_regla VARCHAR(60) NOT NULL UNIQUE,
    nombre_regla VARCHAR(150) NOT NULL,
    descripcion TEXT NOT NULL,
    entidad_origen VARCHAR(50) NOT NULL,
    entidad_destino VARCHAR(50) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    severidad VARCHAR(20) NOT NULL DEFAULT 'ALTA',
    parametros_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    acciones_sugeridas JSONB NOT NULL DEFAULT '[]'::jsonb,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.cat_regla_relacion (codigo_regla, nombre_regla, descripcion, entidad_origen, entidad_destino, activa, severidad, parametros_json, acciones_sugeridas)
VALUES
    ('ESTUDIANTE_PROGRAMA_PERIODO', 'Estudiante ↔ Programa / Módulo',
     'El POS o módulo existe en el catálogo y la fecha de la fila cae dentro del período del programa.',
     'ESTUDIANTE', 'PROGRAMA', TRUE, 'ALTA',
     '{"validar_pos": true, "validar_periodo": true, "tolerancia_meses": 12}'::jsonb,
     '["VINCULAR_PROGRAMA", "CORREGIR_FECHA", "MARCAR_SIN_DATO"]'::jsonb),
    ('MODULO_EN_PROGRAMA', 'Módulo ↔ Programa',
     'El número de módulo existe para ese POS en el catálogo de módulos.',
     'MODULO', 'PROGRAMA', TRUE, 'ALTA',
     '{"validar_numero_modulo": true}'::jsonb,
     '["VINCULAR_MODULO", "MARCAR_SIN_DATO"]'::jsonb),
    ('DOCENTE_MODULO_BRIDGE', 'Docente ↔ Módulo',
     'El docente está en bridge_modulo_docente para ese módulo o se marca DOCENTE_SIN_VINCULAR.',
     'DOCENTE', 'MODULO', TRUE, 'MEDIA',
     '{"motivo_sin_vincular": "DOCENTE_SIN_VINCULAR"}'::jsonb,
     '["VINCULAR_DOCENTE", "MARCAR_SIN_DATO"]'::jsonb),
    ('PAGO_INSCRIPCION_PROGRAMA', 'Pago ↔ Inscripción',
     'La persona de una fila financiera está inscrita en ese programa.',
     'PAGO', 'INSCRIPCION', TRUE, 'ALTA',
     '{"categorias": ["financiero"]}'::jsonb,
     '["VINCULAR_INSCRIPCION", "MARCAR_SIN_DATO"]'::jsonb),
    ('RESPUESTA_ESCALA_PREGUNTA', 'Respuesta ↔ Escala',
     'La puntuación cabe dentro de la escala declarada de la pregunta.',
     'RESPUESTA', 'ESCALA', TRUE, 'ALTA',
     '{"escala_min": 1}'::jsonb,
     '["CORREGIR_PUNTUACION", "MARCAR_SIN_DATO"]'::jsonb),
    ('FECHA_GESTION_VALIDA', 'Fecha ↔ Gestión',
     'La fecha de la fila cae en una gestión académica válida (no 0205, 2580 ni 3035).',
     'FECHA', 'GESTION', TRUE, 'ALTA',
     '{"anio_min": 2015, "anio_max": 2030, "anios_invalidos": [205, 2580, 3035]}'::jsonb,
     '["CORREGIR_FECHA", "MARCAR_SIN_DATO"]'::jsonb)
ON CONFLICT (codigo_regla) DO UPDATE SET
    nombre_regla = EXCLUDED.nombre_regla,
    descripcion = EXCLUDED.descripcion,
    parametros_json = EXCLUDED.parametros_json,
    acciones_sugeridas = EXCLUDED.acciones_sugeridas;
