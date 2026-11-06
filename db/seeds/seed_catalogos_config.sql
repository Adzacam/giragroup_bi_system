-- =============================================================================
-- CONFIGURACIÓN CURADA DE INGESTA (no son datos institucionales)
-- Reglas de clasificación, mapeo base de columnas y plantillas de texto plano.
-- populate_catalogos.py la anexa a seed_catalogos.sql y enriquece el mapeo de
-- columnas con las cabeceras observadas en uploads/data.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 12. Etiquetas y Reglas de Clasificación (cat_etiqueta_clasificacion)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_etiqueta_clasificacion (categoria, subtipo, palabra_clave, ambito, peso) VALUES
    ('academico', 'ACTAS_NOTAS', 'acta', 'AMBOS', 4),
    ('academico', 'ACTAS_NOTAS', 'actas', 'AMBOS', 4),
    ('academico', 'ACTAS_NOTAS', 'acta de notas', 'AMBOS', 5),
    ('academico', 'ACTAS_NOTAS', 'nota', 'AMBOS', 3),
    ('academico', 'ACTAS_NOTAS', 'calificacion', 'AMBOS', 3),
    ('academico', 'ACTAS_NOTAS', 'calificaciones', 'AMBOS', 3),
    ('academico', 'ACTAS_NOTAS', 'asistencia', 'AMBOS', 2),
    ('academico', 'ACTAS_NOTAS', 'materia', 'AMBOS', 2),
    ('academico', 'ACTAS_NOTAS', 'alumno', 'AMBOS', 2),
    ('academico', 'ACTAS_NOTAS', 'estudiante', 'AMBOS', 2),
    ('academico', 'ACTAS_NOTAS', 'arca', 'AMBOS', 3),
    ('academico', 'ACTAS_NOTAS', 'academ', 'AMBOS', 2),
    ('academico', 'ACTAS_NOTAS', 'módulo 1', 'HOJA', 3),
    ('academico', 'ACTAS_NOTAS', 'modulo 1', 'HOJA', 3),
    ('academico', 'EVALUACION_DOCENTE', 'evaluacion docente', 'AMBOS', 5),
    ('academico', 'EVALUACION_DOCENTE', 'evaluación docente', 'AMBOS', 5),
    ('academico', 'EVALUACION_DOCENTE', 'docente mostró', 'CONTENIDO', 4),
    ('academico', 'EVALUACION_DOCENTE', 'estilo de enseñanza', 'CONTENIDO', 4),
    ('academico', 'EVALUACION_DOCENTE', 'explica', 'CONTENIDO', 3),
    ('academico', 'EVALUACION_DOCENTE', 'recomiende el presente', 'CONTENIDO', 4),
    ('academico', 'EVALUACION_DOCENTE', '1. ¿la/el', 'CONTENIDO', 4),
    ('academico', 'DOCENTE_MODULO', 'tipo de docente', 'CONTENIDO', 4),
    ('academico', 'DOCENTE_MODULO', 'pago docente', 'CONTENIDO', 4),
    ('academico', 'DOCENTE_MODULO', 'fecha inicio', 'CONTENIDO', 2),
    ('academico', 'DOCENTE_MODULO', 'pos - modulo', 'CONTENIDO', 4),
    ('academico', 'DOCENTE_MODULO', 'módulo', 'AMBOS', 2),
    ('academico', 'DOCENTE_MODULO', 'modulo', 'AMBOS', 2),
    ('academico', 'DOCENTE_MODULO', 'docente', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'cuota', 'AMBOS', 3),
    ('financiero', 'COBRANZAS', 'cuota postgrado', 'AMBOS', 4),
    ('financiero', 'COBRANZAS', 'monto', 'AMBOS', 3),
    ('financiero', 'COBRANZAS', 'monto cobrado', 'AMBOS', 4),
    ('financiero', 'COBRANZAS', 'factura', 'AMBOS', 3),
    ('financiero', 'COBRANZAS', 'n° de factura', 'AMBOS', 4),
    ('financiero', 'COBRANZAS', 'fecha de facturación', 'AMBOS', 4),
    ('financiero', 'COBRANZAS', 'razón social', 'AMBOS', 3),
    ('financiero', 'COBRANZAS', 'ingreso', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'egreso', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'techo', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'cobranza', 'AMBOS', 3),
    ('financiero', 'COBRANZAS', 'cobranzas', 'AMBOS', 4),
    ('financiero', 'COBRANZAS', 'saldo', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'deuda', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'presupuest', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'ejecutado', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'costo', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'gasto', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'pago', 'AMBOS', 2),
    ('financiero', 'COBRANZAS', 'financier', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'lead', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'interesado', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'inscripción', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'inscripcion', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'inscrito', 'AMBOS', 4),
    ('comercial', 'INSCRIPCIONES', 'inscripto', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'tbl_inscritos', 'AMBOS', 4),
    ('comercial', 'INSCRIPCIONES', 'meta', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'venta', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'prospecto', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'crm', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'marketing', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'campana', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'contacto', 'AMBOS', 2),
    ('comercial', 'INSCRIPCIONES', 'matricul', 'AMBOS', 3),
    ('comercial', 'INSCRIPCIONES', 'marca temporal', 'CONTENIDO', 4),
    ('comercial', 'INSCRIPCIONES', 'numeroproyecto', 'CONTENIDO', 4)
ON CONFLICT (palabra_clave) DO UPDATE 
SET categoria = EXCLUDED.categoria,
    subtipo = EXCLUDED.subtipo,
    ambito = EXCLUDED.ambito,
    peso = EXCLUDED.peso;

-- -----------------------------------------------------------------------------
-- 13. Mapeo Canónico de Columnas (cat_mapeo_columna)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_mapeo_columna (campo_canonico, alias_columna, tipo_entidad) VALUES
    ('ESTUDIANTE', 'nombre', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'nombres', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'nombre completo', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'estudiante', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'alumno', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'postulante', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'participante', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'cliente', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'razón social', 'ESTUDIANTE'),
    ('ESTUDIANTE', 'razon social', 'ESTUDIANTE'),
    ('PATERNO', 'paterno', 'ESTUDIANTE'),
    ('PATERNO', 'ap_paterno', 'ESTUDIANTE'),
    ('PATERNO', 'apellido paterno', 'ESTUDIANTE'),
    ('MATERNO', 'materno', 'ESTUDIANTE'),
    ('MATERNO', 'ap_materno', 'ESTUDIANTE'),
    ('MATERNO', 'apellido materno', 'ESTUDIANTE'),
    ('CI', 'ci', 'CI'),
    ('CI', 'cédula', 'CI'),
    ('CI', 'cedula', 'CI'),
    ('CI', 'identidad', 'CI'),
    ('CI', 'c.i.', 'CI'),
    ('CI', 'nit', 'CI'),
    ('POS', 'pos', 'POS'),
    ('POS', 'codigo pos', 'POS'),
    ('POS', 'código pos', 'POS'),
    ('POS', 'proyecto', 'POS'),
    ('POS', 'numeroproyecto', 'POS'),
    ('POS', 'pos - modulo', 'POS'),
    ('PROGRAMA', 'programa', 'PROGRAMA'),
    ('PROGRAMA', 'nombre programa', 'PROGRAMA'),
    ('PROGRAMA', 'carrera', 'PROGRAMA'),
    ('MODULO', 'módulo', 'MODULO'),
    ('MODULO', 'modulo', 'MODULO'),
    ('MODULO', 'nro modulo', 'MODULO'),
    ('MODULO', 'materia', 'MODULO'),
    ('NOTA', 'nota', 'NOTA'),
    ('NOTA', 'calificación', 'NOTA'),
    ('NOTA', 'calificacion', 'NOTA'),
    ('NOTA', 'nota final', 'NOTA'),
    ('NOTA', 'promedio', 'NOTA'),
    ('ESTADO', 'estado', 'OTRO'),
    ('ESTADO', 'estado academico', 'OTRO'),
    ('ESTADO', 'condicion', 'OTRO'),
    ('ESTADO', 'situacion', 'OTRO'),
    ('MONTO', 'monto', 'MONTO'),
    ('MONTO', 'monto cobrado', 'MONTO'),
    ('MONTO', 'total', 'MONTO'),
    ('MONTO', 'saldo', 'MONTO'),
    ('MONTO', 'cuota', 'MONTO'),
    ('MONTO', 'cuota postgrado', 'MONTO'),
    ('FACTURA', 'factura', 'FACTURA'),
    ('FACTURA', 'n° de factura', 'FACTURA'),
    ('FACTURA', 'numero factura', 'FACTURA'),
    ('FACTURA', 'nro factura', 'FACTURA'),
    ('FECHA', 'fecha', 'FECHA'),
    ('FECHA', 'fecha de facturación', 'FECHA'),
    ('FECHA', 'marca temporal', 'FECHA'),
    ('FECHA', 'fecha inicio', 'FECHA'),
    ('DOCENTE', 'docente', 'DOCENTE'),
    ('DOCENTE', 'profesor', 'DOCENTE'),
    ('DOCENTE', 'facilitador', 'DOCENTE'),
    ('ASESOR', 'asesor', 'OTRO'),
    ('ASESOR', 'ejecutivo', 'OTRO')
ON CONFLICT (alias_columna) DO UPDATE 
SET campo_canonico = EXCLUDED.campo_canonico,
    tipo_entidad = EXCLUDED.tipo_entidad;

-- -----------------------------------------------------------------------------
-- 14. Guías y Plantillas Dinámicas para Texto Plano (cat_guia_texto_plano)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_guia_texto_plano (subtipo, descripcion, plantilla_texto, campos_requeridos, prioridad) VALUES
(
    'ACTAS_NOTAS',
    'Guía para actas de calificaciones y rendimiento académico',
    'En el programa {PROGRAMA} (código {POS}), el estudiante {ESTUDIANTE} (CI {CI}) registró las calificaciones {NOTAS}, con estado académico {ESTADO}.',
    'ESTUDIANTE,PROGRAMA,POS,NOTAS',
    1
),
(
    'EVALUACION_DOCENTE',
    'Guía para encuestas de percepción y evaluación docente',
    'En la evaluación docente del programa {PROGRAMA} (código {POS}), módulo {MODULO}, el estudiante {ESTUDIANTE} emitió su evaluación en fecha {FECHA} con respuestas: {RESPUESTAS}.',
    'ESTUDIANTE,PROGRAMA,POS,MODULO',
    2
),
(
    'COBRANZAS',
    'Guía para transacciones financieras, facturación y cobranzas de cuotas',
    'Se registró cobranza por un monto de {MONTO} Bs en fecha {FECHA} para el cliente {ESTUDIANTE} (CI/NIT {CI}) correspondiente al programa {PROGRAMA} (código {POS}) bajo factura N° {FACTURA} por concepto de {CONCEPTO}.',
    'MONTO,ESTUDIANTE,PROGRAMA,FECHA',
    3
),
(
    'INSCRIPCIONES',
    'Guía para registros comerciales de prospección e inscripciones',
    'En fecha {FECHA}, se registró la inscripción del postulante {ESTUDIANTE} (CI {CI}) en el programa {PROGRAMA} (código {POS}) asesorado por {ASESOR}.',
    'ESTUDIANTE,PROGRAMA,POS,FECHA',
    4
),
(
    'DOCENTE_MODULO',
    'Guía para asignación y honorarios docentes por módulo',
    'Para el programa {PROGRAMA} (código {POS}), el docente {DOCENTE} fue asignado al módulo {MODULO} con fecha de inicio {FECHA} y pago programado de {MONTO} Bs.',
    'DOCENTE,PROGRAMA,MODULO',
    5
),
(
    'GENERICO',
    'Plantilla estructurada de fallback para bloques tabulares no tipificados',
    'Registro en hoja {HOJA}: {DETALLES}.',
    'HOJA,DETALLES',
    99
)
ON CONFLICT (subtipo) DO UPDATE 
SET descripcion = EXCLUDED.descripcion,
    plantilla_texto = EXCLUDED.plantilla_texto,
    campos_requeridos = EXCLUDED.campos_requeridos,
    prioridad = EXCLUDED.prioridad;

