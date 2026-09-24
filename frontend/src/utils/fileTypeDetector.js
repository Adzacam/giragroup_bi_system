/**
 * fileTypeDetector.js
 * -------------------
 * Utilidad de detección inteligente del tipo documental institucional
 * para el pipeline de ingesta DataOps de GIRAGROUP BI System.
 */

export const SOURCE_TYPE_LABELS = {
  EXCEL_ACTA: 'Acta de Calificaciones (Excel)',
  FORMS_INSCRIPCIONES: 'Inscripciones (Google Forms)',
  MOODLE_AULA: 'Reporte de Aula Virtual (Moodle)',
  SHEETS_COBRANZA: 'Cartera de Cobranza (Sheets)',
};

export const SOURCE_TYPES = [
  SOURCE_TYPE_LABELS.EXCEL_ACTA,
  SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES,
  SOURCE_TYPE_LABELS.MOODLE_AULA,
  SOURCE_TYPE_LABELS.SHEETS_COBRANZA,
];

/**
 * Detecta inteligentemente la fuente documental a partir del nombre, extensión y metadatos del archivo.
 * 
 * Reglas de clasificación:
 * 1. Moodle: si contiene 'moodle', 'grades' o extensión '.xml' -> Reporte de Aula Virtual (Moodle)
 * 2. Cartera / Cobranza: si contiene 'cobranza', 'cartera', 'cuotas', 'pagos', 'mora' -> Cartera de Cobranza (Sheets)
 * 3. Formularios: si contiene 'form', 'encuesta', 'respuestas', 'inscrip' o es '.csv' -> Inscripciones (Google Forms)
 * 4. Actas de Calificación: si es '.xlsx', '.xls' o contiene 'acta', 'pos', 'calif', 'notas' -> Acta de Calificaciones (Excel)
 * 5. Fallback predeterminado según extensión.
 * 
 * @param {File|string} file - Objeto File de HTML5 o string con el nombre del archivo
 * @returns {string} Nombre canónico del tipo documental
 */
export function detectSourceType(file) {
  if (!file) return SOURCE_TYPE_LABELS.EXCEL_ACTA;

  const fileName = typeof file === 'string' ? file : (file.name || '');
  const lowerName = fileName.toLowerCase().trim();
  
  // Extraer extensión
  const lastDot = lowerName.lastIndexOf('.');
  const ext = lastDot !== -1 ? lowerName.substring(lastDot) : '';

  // 1. Regla Moodle
  const moodleKeywords = ['moodle', 'grades'];
  if (moodleKeywords.some(kw => lowerName.includes(kw)) || ext === '.xml') {
    return SOURCE_TYPE_LABELS.MOODLE_AULA;
  }

  // 2. Regla Cartera / Cobranza
  const cobranzaKeywords = ['cobranza', 'cartera', 'cuotas', 'pagos', 'mora'];
  if (cobranzaKeywords.some(kw => lowerName.includes(kw))) {
    return SOURCE_TYPE_LABELS.SHEETS_COBRANZA;
  }

  // 3. Regla Formularios / Inscripciones
  const formsKeywords = ['form', 'encuesta', 'respuestas', 'inscrip'];
  if (formsKeywords.some(kw => lowerName.includes(kw))) {
    return SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES;
  }

  // 4. Regla Actas de Calificaciones
  const actaKeywords = ['acta', 'pos', 'calif', 'notas'];
  if (actaKeywords.some(kw => lowerName.includes(kw))) {
    return SOURCE_TYPE_LABELS.EXCEL_ACTA;
  }

  // 5. Fallback por extensión
  if (ext === '.csv') {
    return SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES;
  }
  if (ext === '.xlsx' || ext === '.xls') {
    return SOURCE_TYPE_LABELS.EXCEL_ACTA;
  }
  if (ext === '.xml') {
    return SOURCE_TYPE_LABELS.MOODLE_AULA;
  }

  return SOURCE_TYPE_LABELS.EXCEL_ACTA;
}

/**
 * Formatea el tamaño en bytes a KB o MB legibles
 * @param {number} bytes 
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 KB';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Retorna metadatos de estilo (color de badge, icono) según el tipo documental
 * @param {string} type 
 */
export function getSourceTypeMeta(type) {
  switch (type) {
    case SOURCE_TYPE_LABELS.EXCEL_ACTA:
      return {
        bg: '#dcfce7',
        color: '#15803d',
        shortName: 'Excel Acta',
        extension: '.xlsx'
      };
    case SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES:
      return {
        bg: '#e0e7ff',
        color: '#4338ca',
        shortName: 'Google Forms',
        extension: '.csv'
      };
    case SOURCE_TYPE_LABELS.MOODLE_AULA:
      return {
        bg: '#ffedd5',
        color: '#c2410c',
        shortName: 'Moodle',
        extension: '.csv/.xml'
      };
    case SOURCE_TYPE_LABELS.SHEETS_COBRANZA:
      return {
        bg: '#fef3c7',
        color: '#b45309',
        shortName: 'Cartera Sheets',
        extension: '.xlsx'
      };
    default:
      return {
        bg: 'var(--color-mist-gray)',
        color: 'var(--color-ink-black)',
        shortName: 'Documento',
        extension: ''
      };
  }
}
