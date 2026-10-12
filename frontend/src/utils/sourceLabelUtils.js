/**
 * GIRAGROUP BI System - Utilidad de Mapeo de Fuentes y Dominios de Negocio
 * Mapea nombres de archivos y tipos heterogéneos a sus dominios funcionales del modelo Constelación
 * y proporciona etiquetas de negocio comprensibles para la interfaz de usuario.
 */

export const SOURCE_TABLE_MAPPINGS = {
  // Catálogos y Dimensiones
  DIM_ESTUDIANTE: {
    table: 'Catálogo de Estudiantes',
    tableType: 'CATÁLOGO',
    color: '#0284c7',
    bgColor: 'rgba(2, 132, 199, 0.12)',
    borderColor: 'rgba(2, 132, 199, 0.3)',
    category: 'Admisiones & Estudiantes',
  },
  DIM_MODULO: {
    table: 'Catálogo de Módulos',
    tableType: 'CATÁLOGO',
    color: '#d97706',
    bgColor: 'rgba(217, 119, 6, 0.12)',
    borderColor: 'rgba(217, 119, 6, 0.3)',
    category: 'Estructura Curricular',
  },
  DIM_DOCENTE: {
    table: 'Catálogo de Docentes',
    tableType: 'CATÁLOGO',
    color: '#7c3aed',
    bgColor: 'rgba(124, 58, 237, 0.12)',
    borderColor: 'rgba(124, 58, 237, 0.3)',
    category: 'Cuerpo Académico',
  },
  DIM_PROGRAMA: {
    table: 'Catálogo de Programas',
    tableType: 'CATÁLOGO',
    color: '#059669',
    bgColor: 'rgba(5, 150, 105, 0.12)',
    borderColor: 'rgba(5, 150, 105, 0.3)',
    category: 'Programas de Posgrado',
  },
  // Dominios de Hechos
  FACT_RENDIMIENTO: {
    table: 'Rendimiento Académico',
    tableType: 'INDICADORES',
    color: '#1b8754',
    bgColor: 'rgba(27, 135, 84, 0.12)',
    borderColor: 'rgba(27, 135, 84, 0.3)',
    category: 'Rendimiento y Calificaciones',
  },
  FACT_FLUJO_CAJA: {
    table: 'Situación Financiera y Cobranzas',
    tableType: 'FINANZAS',
    color: '#5d2a1a',
    bgColor: 'rgba(93, 42, 26, 0.12)',
    borderColor: 'rgba(93, 42, 26, 0.3)',
    category: 'Finanzas & Recaudación',
  },
  FACT_ASISTENCIA: {
    table: 'Control de Asistencia',
    tableType: 'ACADÉMICO',
    color: '#0891b2',
    bgColor: 'rgba(8, 145, 178, 0.12)',
    borderColor: 'rgba(8, 145, 178, 0.3)',
    category: 'Asistencia y Participación',
  },
};

/**
 * Detecta el dominio funcional de negocio a partir del nombre del archivo y tipo.
 * @param {string} fileName Nombre del archivo crudo (ej: "Planificacion_Ejecucion_TEST.xlsx")
 * @param {string} fileType Tipo de fuente detectada (ej: "Excel Acta", "Google Forms", "Aula Moodle")
 * @returns {object} Metadatos completos de mapeo al dominio funcional
 */
export function getSourceTableMeta(fileName = '', fileType = '') {
  const nameLower = (fileName || '').toLowerCase();
  const typeLower = (fileType || '').toLowerCase();

  // 1. Finanzas / Situación Financiera y Cobranzas
  if (
    nameLower.includes('cobranza') ||
    nameLower.includes('egreso') ||
    nameLower.includes('techo') ||
    nameLower.includes('ejecutado') ||
    nameLower.includes('cuota') ||
    nameLower.includes('pago') ||
    nameLower.includes('mora') ||
    typeLower.includes('cartera')
  ) {
    let domainTitle = 'Cartera de Cobranzas y Recaudación';
    if (nameLower.includes('egreso')) domainTitle = 'Control de Egresos y Flujo Operativo';
    else if (nameLower.includes('techo')) domainTitle = 'Techos Presupuestarios & Metas';
    else if (nameLower.includes('ejecutado')) domainTitle = 'Ejecución Presupuestaria vs. Metas';

    return {
      ...SOURCE_TABLE_MAPPINGS.FACT_FLUJO_CAJA,
      domainTitle,
      rawFileName: fileName,
      description: 'Asignación a Situación Financiera y Cobranzas (Transacciones, cuotas y pagos)',
    };
  }

  // 2. Docentes
  if (nameLower.includes('docente') || nameLower.includes('profesor') || nameLower.includes('facilitador')) {
    let domainTitle = 'Evaluación de Desempeño Docente';
    if (nameLower.includes('experiencia')) domainTitle = 'Registro de Experiencia Docente';

    return {
      ...SOURCE_TABLE_MAPPINGS.DIM_DOCENTE,
      domainTitle,
      rawFileName: fileName,
      description: 'Asignación a Catálogo de Docentes (Perfil, experiencia y evaluaciones)',
    };
  }

  // 3. Estudiantes / Admisiones / Inscripciones
  if (
    nameLower.includes('inscrit') ||
    nameLower.includes('admision') ||
    nameLower.includes('postulant') ||
    nameLower.includes('forms') ||
    nameLower.includes('formulario') ||
    typeLower.includes('forms') ||
    (nameLower.endsWith('.csv') && (nameLower.includes('inscrip') || nameLower.includes('alumno')))
  ) {
    let domainTitle = 'Padrón de Inscritos y Postulantes';
    if (nameLower.includes('forms') || typeLower.includes('forms')) {
      domainTitle = 'Formulario de Admisión e Inscripción';
    }

    return {
      ...SOURCE_TABLE_MAPPINGS.DIM_ESTUDIANTE,
      domainTitle,
      rawFileName: fileName,
      description: 'Asignación a Catálogo de Estudiantes (Datos personales, CI, contacto)',
    };
  }

  // 4. Módulos / Planificación Curricular / OKRs
  if (
    nameLower.includes('planific') ||
    nameLower.includes('ejecucion') ||
    nameLower.includes('modulo') ||
    nameLower.includes('materia') ||
    nameLower.includes('curricular') ||
    nameLower.includes('okr')
  ) {
    return {
      ...SOURCE_TABLE_MAPPINGS.DIM_MODULO,
      domainTitle: 'Planificación Curricular & OKRs',
      rawFileName: fileName,
      description: 'Asignación a Catálogo de Módulos (Estructura de programa y créditos)',
    };
  }

  // 5. Asistencia
  if (nameLower.includes('asist') || nameLower.includes('arca')) {
    return {
      ...SOURCE_TABLE_MAPPINGS.FACT_ASISTENCIA,
      domainTitle: 'Control de Asistencia y Participación',
      rawFileName: fileName,
      description: 'Asignación a Control de Asistencia por Sesión',
    };
  }

  // 6. Calificaciones / Rendimiento Académico (Moodle o Actas Excel)
  if (
    typeLower.includes('moodle') ||
    nameLower.includes('moodle') ||
    nameLower.includes('grades') ||
    nameLower.endsWith('.xml')
  ) {
    return {
      ...SOURCE_TABLE_MAPPINGS.FACT_RENDIMIENTO,
      domainTitle: 'Evaluación LMS Aula Virtual (Moodle)',
      rawFileName: fileName,
      description: 'Asignación a Rendimiento Académico (Libro de calificaciones virtual)',
    };
  }

  // Fallback por defecto: Actas de Calificaciones
  return {
    ...SOURCE_TABLE_MAPPINGS.FACT_RENDIMIENTO,
    domainTitle: 'Acta Oficial de Calificaciones y Notas',
    rawFileName: fileName,
    description: 'Asignación a Rendimiento Académico (Notas finales de módulo)',
  };
}

/**
 * Retorna la etiqueta funcional de la entidad según el tipo detectado en HITL
 * @param {string} tipoEntidad 'ESTUDIANTE' | 'MODULO' | 'DOCENTE' | 'CONCEPTO_FINANCIERO'
 */
export function getEntityTargetTableBadge(tipoEntidad = '') {
  const norm = (tipoEntidad || '').toUpperCase();
  switch (norm) {
    case 'MODULO':
      return {
        table: 'Catálogo de Módulos',
        label: 'Módulo Académico',
        color: '#d97706',
        bgColor: 'rgba(217, 119, 6, 0.12)',
        borderColor: 'rgba(217, 119, 6, 0.3)',
      };
    case 'DOCENTE':
      return {
        table: 'Catálogo de Docentes',
        label: 'Plantel Docente',
        color: '#7c3aed',
        bgColor: 'rgba(124, 58, 237, 0.12)',
        borderColor: 'rgba(124, 58, 237, 0.3)',
      };
    case 'CONCEPTO_FINANCIERO':
      return {
        table: 'Situación Financiera y Cobranzas',
        label: 'Concepto Financiero',
        color: '#5d2a1a',
        bgColor: 'rgba(93, 42, 26, 0.12)',
        borderColor: 'rgba(93, 42, 26, 0.3)',
      };
    case 'ESTUDIANTE':
    default:
      return {
        table: 'Catálogo de Estudiantes',
        label: 'Estudiante / Postulante',
        color: '#0284c7',
        bgColor: 'rgba(2, 132, 199, 0.12)',
        borderColor: 'rgba(2, 132, 199, 0.3)',
      };
  }
}
