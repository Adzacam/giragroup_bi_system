-- =============================================================================
-- INSERCIÓN DE CATÁLOGOS INSTITUCIONALES (3NF) - giragroup_catalog_db
-- Oferta curricular y claustro docente de Unifranz Postgrado y Gira Group S.R.L.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Inserción de Escuelas Académicas (cat_escuela)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_escuela (nombre_escuela, sigla)
VALUES 
    ('Escuela de Negocios y Ciencias Económicas', 'ENAC'),
    ('Escuela de Salud y Ciencias Médicas', 'ESAL'),
    ('Escuela de Ciencias Jurídicas y Sociales', 'ECJS'),
    ('Escuela de Ingeniería y Tecnología', 'EITEC'),
    ('Escuela de Educación y Humanidades', 'EEHUM'),
    ('Ciencias de la Salud', 'ECS'),
    ('Ingeniería y Tecnología', 'EITE'),
    ('Negocios y Economía', 'ENE'),
    ('Educación y Humanidades', 'EEH')
ON CONFLICT (nombre_escuela) DO UPDATE 
SET sigla = EXCLUDED.sigla;

-- -----------------------------------------------------------------------------
-- 2. Inserción de Tipos de Programa (cat_tipo_programa)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_tipo_programa (nombre_tipo)
VALUES 
    ('Diplomado'),
    ('DIPLOMADO'),
    ('Maestría'),
    ('MAESTRÍA'),
    ('Especialidad'),
    ('Formación Continua y Desarrollo Profesional'),
    ('CURSO EXPERTO / CERTIFICACIÓN'),
    ('Curso')
ON CONFLICT (nombre_tipo) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Inserción de Modalidades de Impartición (cat_modalidad)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_modalidad (nombre_modalidad)
VALUES 
    ('Virtual Sincrónica'),
    ('VIRTUAL SINCRÓNICA'),
    ('Semipresencial / Híbrida'),
    ('SEMIPRESENCIAL / HÍBRIDA'),
    ('Presencial'),
    ('Virtual Asincrónica')
ON CONFLICT (nombre_modalidad) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 4. Inserción de Docentes Institucionales Verificados (cat_docente)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_docente (nombre_completo, email, celular, grado_academico, tipo_docente)
VALUES 
    (
        'Marco Antonio Jiménez Gira', 
        'marco.jimenez@giragroup.bo', 
        '+591 76200111', 
        'Licenciado en Informática / Microsoft Certified Trainer (MCT) / MOS Expert', 
        'TITULAR'
    ),
    (
        'Luis Fernando San Juan Bernal', 
        'luis.sanjuan@growbolivia.com', 
        '+591 77200222', 
        'Master of Business Administration (MBA) / Ingeniero Comercial / SFC', 
        'TITULAR'
    ),
    (
        'Wilmer Campos Saavedra', 
        'wilmer.campos@unifranz.edu.bo', 
        '+591 70155667', 
        'Magíster en Educación Superior y Calidad Académica', 
        'TITULAR'
    ),
    (
        'Guillermo Rivera Álvarez', 
        'guillermo.rivera@postgrado.unifranz.edu.bo', 
        '+591 72088990', 
        'Médico Especialista en Cirugía Estética y Reparadora', 
        'TITULAR'
    ),
    (
        'Sara Yoshino Gómez', 
        'sara.yoshino@unifranz.edu.bo', 
        '+591 73044112', 
        'Especialista en Estética y Dermatología Clínica', 
        'ADJUNTO'
    ),
    (
        'Mónica Dupleix Landívar', 
        'monica.dupleix@bmgroup.bo', 
        '+591 71599884', 
        'Licenciada en Psicología Organizacional / Consultora en Talento Humano', 
        'INVITADO'
    ),
    (
        'Roger Dante Rodríguez Callisaya', 
        'roger.rodriguez@unifranz.edu.bo', 
        '+591 78912345', 
        'Magíster en Tecnologías de Información e Innovación', 
        'TITULAR'
    )
ON CONFLICT (nombre_completo) DO UPDATE 
SET email = EXCLUDED.email,
    celular = EXCLUDED.celular,
    grado_academico = EXCLUDED.grado_academico,
    tipo_docente = EXCLUDED.tipo_docente;

-- -----------------------------------------------------------------------------
-- 5. Inserción de Programas Canónicos (cat_programa)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_programa (
    pos_code, 
    nombre_programa, 
    version, 
    nombre_completo_raw, 
    id_escuela, 
    id_tipo_programa, 
    id_modalidad, 
    inversion_base, 
    punto_equilibrio, 
    horas_totales
)
VALUES 
    -- 1. Marketing Analytics
    (
        'DIP-MKT-ANL', 
        'Diplomado en Marketing Analytics', 
        1, 
        'Diplomado en Marketing Analytics y Estrategia Basada en Datos - Versión I', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ENAC', 'ENE') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1), 
        4800.00, 
        14, 
        400
    ),
    -- 2. Educación Superior y TICs
    (
        'DIP-EDS-TEC', 
        'Diplomado en Educación Superior y Tecnologías del Aprendizaje', 
        1, 
        'Diplomado en Educación Superior Mención Tecnologías en la Educación Superior - Versión I', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EEHUM', 'EEH') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Semipresencial%' LIMIT 1), 
        4200.00, 
        16, 
        800
    ),
    -- 3. Sistemas Contra Incendios
    (
        'DIP-ING-PCI', 
        'Diplomado en Ingeniería en Sistemas de Prevención y Protección Contra Incendios', 
        3, 
        'Diplomado en Ingeniería en Sistemas de Prevención y Protección Contra Incendios SIPPCI - Versión III', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EITEC', 'EITE') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Semipresencial%' LIMIT 1), 
        5500.00, 
        12, 
        450
    ),
    -- 4. Seguridad en Trabajos de Alto Riesgo
    (
        'DIP-SEG-IND', 
        'Diplomado en Seguridad en Trabajos de Alto Riesgo', 
        7, 
        'Diplomado en Seguridad y Salud Ocupacional en Trabajos de Alto Riesgo (SySO) - 7ma Versión', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EITEC', 'EITE') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1), 
        4600.00, 
        15, 
        400
    ),
    -- 5. Redes y Ciberseguridad de Datos
    (
        'DIP-RED-CIB', 
        'Diplomado en Redes y Ciberseguridad de Datos', 
        2, 
        'Diplomado en Redes, Seguridad Perimetral y Ciberseguridad de Datos - Versión II', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EITEC', 'EITE') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1), 
        5200.00, 
        13, 
        420
    ),
    -- 6. Asesoría Jurídica Corporativa
    (
        'DIP-JUR-COR', 
        'Diplomado en Asesoría Jurídica Corporativa y Compliance', 
        1, 
        'Diplomado en Asesoría Jurídica Corporativa, Negociación y Cumplimiento Normativo - Versión I', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla = 'ECJS' LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1), 
        4900.00, 
        14, 
        400
    ),
    -- 7. Medicina Estética Facial y Corporal
    (
        'DIP-MED-EST', 
        'Diplomado en Medicina Estética Facial y Corporal', 
        8, 
        'Diplomado Internacional en Medicina Estética Facial y Corporal - 8va Versión', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ESAL', 'ECS') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE 'Presencial' LIMIT 1), 
        8500.00, 
        10, 
        550
    ),
    -- 8. Experto en Dirección de Negocios MYPE
    (
        'EXP-DIR-MYP', 
        'Experto en Dirección de Negocios MYPE y Omnicanalidad', 
        1, 
        'Programa Avanzado de Experto en Dirección de Negocios MYPE y Gestión Omnicanal', 
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ENAC', 'ENE') LIMIT 1), 
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE '%Formación Continua%' OR nombre_tipo ILIKE '%CERTIFICACIÓN%' LIMIT 1), 
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1), 
        2500.00, 
        20, 
        200
    ),
    -- 9. Maestría en Salud Pública
    (
        'MAE-SAL-PUB',
        'Maestría en Salud Pública con Mención en Gerencia en Salud',
        1,
        'Maestría en Salud Pública con Mención en Gerencia en Salud v. I (Unifranz Postgrado)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ESAL', 'ECS') LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Maestría' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Semipresencial%' LIMIT 1),
        16500.00, 
        18, 
        1200
    ),
    -- 10. HVAC Especializado Hospitalario
    (
        'DIP-ING-HVAC',
        'Diplomado en Sistemas HVAC Especializados en Ambientes Críticos Hospitalarios',
        1,
        'Diplomado en Sistemas HVAC Especializados en Ambientes Críticos Hospitalarios (Unifranz)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EITEC', 'EITE') LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        4500.00, 
        12, 
        240
    ),
    -- 11. Derecho Notarial
    (
        'DIP-DER-NOT',
        'Diplomado en Derecho Notarial en Bolivia',
        1,
        'Diplomado en Derecho Notarial en Bolivia (Unifranz Postgrado)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla = 'ECJS' LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        3800.00, 
        15, 
        200
    ),
    -- 12. Derecho Penal
    (
        'DIP-DER-PEN',
        'Diplomado en Derecho Penal y Procesal Penal',
        1,
        'Diplomado en Derecho Penal y Procesal Penal v. I (Unifranz Postgrado)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla = 'ECJS' LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        3900.00, 
        15, 
        200
    ),
    -- 13. Gerencia Comercial
    (
        'DIP-NEG-GCOM',
        'Diplomado en Gerencia Comercial',
        1,
        'Diplomado en Gerencia Comercial (Unifranz Postgrado Santa Cruz)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ENAC', 'ENE') LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        4000.00, 
        14, 
        200
    ),
    -- 14. Negocios Digitales MiPymes (Banco FIE)
    (
        'CUR-EMP-NDIG',
        'Programa de Digitalización y Negocios Digitales para MiPymes',
        1,
        'Programa de Formación en Habilidades Digitales y Negocios (Banco FIE - Unifranz Postgrado)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('ENAC', 'ENE') LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE '%CURSO EXPERTO%' OR nombre_tipo ILIKE '%Formación Continua%' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        0.00, 
        20, 
        120
    ),
    -- 15. Educación Superior y TICs (Versión Alternativa)
    (
        'DIP-EDU-TIC',
        'Diplomado en Educación Superior Mención Tecnologías en la Educación Superior',
        1,
        'Diplomado en Educación Superior Mención TICs v. I (Unifranz Postgrado)',
        (SELECT id_escuela FROM public.cat_escuela WHERE sigla IN ('EEHUM', 'EEH') LIMIT 1),
        (SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo ILIKE 'Diplomado' LIMIT 1),
        (SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad ILIKE '%Virtual Sincrónica%' LIMIT 1),
        3900.00, 
        12, 
        200
    )
ON CONFLICT (pos_code) DO UPDATE 
SET nombre_programa = EXCLUDED.nombre_programa,
    version = EXCLUDED.version,
    nombre_completo_raw = EXCLUDED.nombre_completo_raw,
    inversion_base = EXCLUDED.inversion_base,
    punto_equilibrio = EXCLUDED.punto_equilibrio,
    horas_totales = EXCLUDED.horas_totales;

-- -----------------------------------------------------------------------------
-- 6. Inserción de Módulos Curriculares (cat_modulo)
-- -----------------------------------------------------------------------------
-- Programa 1: DIP-MKT-ANL
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MKT-ANL'), 1, 'Fundamentos de Marketing Analytics en la Estrategia Empresarial', 80.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MKT-ANL'), 2, 'Analítica Web y Comportamiento Digital del Consumidor', 80.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MKT-ANL'), 3, 'Modelos de Decisión Cuantitativa e Investigación de Mercados', 80.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MKT-ANL'), 4, 'Herramientas de Visualización y Modelado de Datos (Power BI y Excel)', 80.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MKT-ANL'), 5, 'Google Analytics Avanzado y Retorno de Inversión (ROI) de Campañas', 80.00, 4800.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 2: DIP-EDS-TEC
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 1, 'Tecnologías Emergentes en el Aula y Educación Basada en Competencias', 130.00, 5200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 2, 'Innovación Curricular y Planificación Didáctica Universitaria', 130.00, 5200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 3, 'Diseño y Gestión de Proyectos Formativos Complejos', 135.00, 5400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 4, 'Estrategias Didácticas Activas y Métodos de Caso en Educación Superior', 135.00, 5400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 5, 'Evaluación Integral del Aprendizaje por Rúbricas y Competencias', 135.00, 5400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-EDS-TEC'), 6, 'Redacción Científica Aplicada a Proyectos Formativos de Grado', 135.00, 5400.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 3: DIP-ING-PCI
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 1, 'Marco Legal, Ley 449, D.S. 2995 y Normativa SIPPCI', 60.00, 4200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 2, 'Hidráulica Aplicada y Redes de Agua Contra Incendios (NFPA 22 y 24)', 65.00, 4500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 3, 'Selección, Simulación e Instalación de Bombas Contra Incendios (NFPA 20)', 65.00, 4500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 4, 'Diseño y Cálculo de Sistemas de Rociadores Automáticos (NFPA 13)', 65.00, 4500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 5, 'Sistemas de Protección mediante Agentes Espumígenos (NFPA 11)', 65.00, 4500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 6, 'Detección Oportuna, Señalización y Alarma de Incendios (NFPA 72)', 65.00, 4500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-ING-PCI'), 7, 'Elaboración de Planos As-Built de Sistemas Contra Incendio', 65.00, 4500.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 4: DIP-SEG-IND
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-SEG-IND'), 1, 'Seguridad y Gestión de Riesgos en Trabajos en Altura', 80.00, 4400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-SEG-IND'), 2, 'Técnicas de Ingreso y Rescate en Espacios Confinados', 80.00, 4400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-SEG-IND'), 3, 'Prevención de Riesgos en Trabajos en Caliente y Soldadura', 80.00, 4400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-SEG-IND'), 4, 'Control de Estabilidad en Excavaciones, Zanjas y Movimiento de Tierras', 80.00, 4400.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-SEG-IND'), 5, 'Seguridad Eléctrica Industrial y Procedimientos de Bloqueo LOTO', 80.00, 4400.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 5: DIP-RED-CIB
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-RED-CIB'), 1, 'Enrutamiento Avanzado y Arquitectura de Redes Corporativas Seguras', 84.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-RED-CIB'), 2, 'Seguridad Perimetral, Cortafuegos y Monitoreo de Intrusiones', 84.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-RED-CIB'), 3, 'Ciberdefensa Operativa, Análisis de Vulnerabilidades y Mitigación', 84.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-RED-CIB'), 4, 'Informática Forense, Preservación de Evidencias y Respuesta a Incidentes', 84.00, 4800.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-RED-CIB'), 5, 'Sistemas de Gestión de Seguridad de la Información (ISO/IEC 27001)', 84.00, 4800.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 6: DIP-JUR-COR
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-JUR-COR'), 1, 'Régimen Societario y Gobierno Corporativo en el Ámbito Boliviano', 80.00, 4600.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-JUR-COR'), 2, 'Contratación Comercial Internacional, Garantías y Negociación', 80.00, 4600.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-JUR-COR'), 3, 'Planificación Fiscal Corporativa y Estrategia Contenciosa Tributaria', 80.00, 4600.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-JUR-COR'), 4, 'Gestión del Derecho Laboral Empresarial y Litigación Corporativa', 80.00, 4600.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-JUR-COR'), 5, 'Compliance Empresarial, Integridad y Métodos de Arbitraje Comercial', 80.00, 4600.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 7: DIP-MED-EST
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MED-EST'), 1, 'Anatomía Facial Aplicada, Bioseguridad y Diagnóstico Estético', 135.00, 7500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MED-EST'), 2, 'Técnicas de Mesoterapia, Intradermoterapia y Renovación Celular', 135.00, 7500.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MED-EST'), 3, 'Aplicación Clínica de Toxina Botulínica y Materiales de Relleno', 140.00, 8000.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'DIP-MED-EST'), 4, 'Dermosustentación con Hilos PDO y Manejo de Complicaciones', 140.00, 8000.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- Programa 8: EXP-DIR-MYP
INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base)
VALUES 
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 1, 'Planificación Estratégica y Modelos de Negocio Rentables', 30.00, 2000.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 2, 'Gestión de Costos, Presupuesto y Flujo de Caja para Mypes', 35.00, 2200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 3, 'Marketing Digital Operativo, Redes Sociales y Conversión en Ventas', 35.00, 2200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 4, 'Gestión Omnicanal y Experiencia de Fidelización de Clientes', 35.00, 2200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 5, 'Eficiencia en Operaciones, Proveedores y Canales de Distribución', 35.00, 2200.00),
    ((SELECT id_programa FROM public.cat_programa WHERE pos_code = 'EXP-DIR-MYP'), 6, 'Habilidades de Liderazgo, Comunicación y Equipos de Alto Rendimiento', 30.00, 2000.00)
ON CONFLICT (id_programa, nro_modulo) DO UPDATE 
SET nombre_modulo = EXCLUDED.nombre_modulo,
    horas_modulo = EXCLUDED.horas_modulo,
    pago_docente_base = EXCLUDED.pago_docente_base;

-- -----------------------------------------------------------------------------
-- 7. Inserción de Criterios Académicos y Estados
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_estado_academico (nombre_estado)
VALUES 
    ('INSCRITO'),
    ('REGULAR_ACTIVO'),
    ('CONCLUIDO_PENDIENTE_MONOGRAFIA'),
    ('GRADUADO_TITULADO'),
    ('REPROBADO'),
    ('RETIRADO_ABANDONO')
ON CONFLICT (nombre_estado) DO NOTHING;

INSERT INTO public.cat_estado_reprobado (nombre_detalle)
VALUES 
    ('REPROBADO_POR_NOTA'),
    ('REPROBADO_POR_ASISTENCIA'),
    ('BAJA_POR_INCUMPLIMIENTO_PAGOS'),
    ('REPROBADO_POR_PLAGIO_ACADEMICO')
ON CONFLICT (nombre_detalle) DO NOTHING;

INSERT INTO public.cat_estado_arca (nombre_arca)
VALUES 
    ('HOMOLOGADO_SISTEMA_NACIONAL'),
    ('EN_TRAMITE_MINISTERIAL'),
    ('NO_APLICA_FORMACION_CONTINUA'),
    ('REGISTRO_ARCHIVADO')
ON CONFLICT (nombre_arca) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 8. Inserción de Tipos de Cartera de Cobranzas (cat_tipo_cartera)
-- -----------------------------------------------------------------------------
INSERT INTO public.cat_tipo_cartera (nombre_cartera, dias_mora_min, dias_mora_max, descripcion)
VALUES 
    ('VIGENTE_AL_DIA', 0, 0, 'Estudiante al día en compromisos arancelarios mensuales'),
    ('MORA_PREVENTIVA', 1, 30, 'Primer ciclo de atraso; recordatorio comercial y seguimiento amigable'),
    ('MORA_ADMINISTRATIVA', 31, 60, 'Segundo ciclo; bloqueo preventivo del aula virtual y gestión formal'),
    ('MORA_PREJUDICIAL', 61, 90, 'Cobranza extrajudicial institucional previa a desvinculación definitiva'),
    ('CARTERA_CASTIGADA_JUDICIAL', 91, 9999, 'Derivación al departamento legal y baja del registro académico')
ON CONFLICT (nombre_cartera) DO UPDATE 
SET dias_mora_min = EXCLUDED.dias_mora_min,
    dias_mora_max = EXCLUDED.dias_mora_max,
    descripcion = EXCLUDED.descripcion;

-- -----------------------------------------------------------------------------
-- 9. Inserción de Metas de Gestión Presupuestaria (ref_metas_gestion)
-- -----------------------------------------------------------------------------
INSERT INTO public.ref_metas_gestion (
    gestion, mes, categoria, monto_meta_ingreso, monto_ejecutado, ebitda_meta_pct, ebitda_ejecutado_pct
)
VALUES 
    (2025, 1, 'POSTGRADO_REGULAR', 120000.00, 115400.00, 0.2800, 0.2650),
    (2025, 1, 'CONVENIOS_CORPORATIVOS', 65000.00, 68900.00, 0.3200, 0.3410),
    (2025, 2, 'POSTGRADO_REGULAR', 140000.00, 138200.00, 0.3000, 0.2920),
    (2025, 2, 'CONVENIOS_CORPORATIVOS', 70000.00, 72500.00, 0.3200, 0.3300),
    (2025, 3, 'POSTGRADO_REGULAR', 180000.00, 175000.00, 0.3100, 0.3050),
    (2025, 3, 'CONVENIOS_CORPORATIVOS', 85000.00, 89000.00, 0.3300, 0.3450)
ON CONFLICT (gestion, mes, categoria) DO UPDATE 
SET monto_meta_ingreso = EXCLUDED.monto_meta_ingreso,
    monto_ejecutado = EXCLUDED.monto_ejecutado,
    ebitda_meta_pct = EXCLUDED.ebitda_meta_pct,
    ebitda_ejecutado_pct = EXCLUDED.ebitda_ejecutado_pct;

COMMIT;
