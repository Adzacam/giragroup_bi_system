/**
 * fileTypeDetector.js
 * -------------------
 * Utilidad de detección determinista del tipo documental institucional
 * priorizando la inspección de cabeceras reales del archivo (#15, #16, #18).
 * Nunca asume "Acta" por defecto cuando las cabeceras no son reconocidas.
 */

import {
  FORMATOS_PERMITIDOS,
  MAX_TAMANO_ARCHIVO_BYTES,
  MAX_TAMANO_ARCHIVO_MB,
} from '../constants/dataopsConfig';

export const SOURCE_TYPE_LABELS = {
  EXCEL_ACTA: 'Acta de Calificaciones (Excel)',
  FORMS_INSCRIPCIONES: 'Inscripciones (Google Forms)',
  MOODLE_AULA: 'Reporte de Aula Virtual (Moodle)',
  SHEETS_COBRANZA: 'Cartera de Cobranza (Sheets)',
};

export const SOURCE_TYPES = [
  SOURCE_TYPE_LABELS.EXCEL_ACTA,
  SOURCE_TYPE_LABELS.MOODLE_AULA,
  SOURCE_TYPE_LABELS.SHEETS_COBRANZA,
  SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES,
];

export const UNRECOGNIZED_SOURCE_LABEL = 'Sin reconocer — Seleccione tipo documental';

/**
 * Convierte cualquier etiqueta o código al código canónico de BD ('ACTA', 'MOODLE', 'COBRANZA', 'ADMISION', o '')
 */
export function toCanonicalSourceCode(type) {
  if (!type) return '';
  const upper = String(type).toUpperCase().trim();
  if (upper === 'ACTA' || type === SOURCE_TYPE_LABELS.EXCEL_ACTA || upper.includes('ACTA')) {
    return 'ACTA';
  }
  if (upper === 'MOODLE' || type === SOURCE_TYPE_LABELS.MOODLE_AULA || upper.includes('MOODLE')) {
    return 'MOODLE';
  }
  if (upper === 'COBRANZA' || type === SOURCE_TYPE_LABELS.SHEETS_COBRANZA || upper.includes('COBRANZA') || upper.includes('CARTERA')) {
    return 'COBRANZA';
  }
  if (upper === 'ADMISION' || type === SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES || upper.includes('INSCRIP') || upper.includes('ADMISION') || upper.includes('FORMS')) {
    return 'ADMISION';
  }
  return '';
}

/**
 * Convierte código canónico a la etiqueta legible del selector
 */
export function toSourceTypeLabel(codeOrLabel) {
  const code = toCanonicalSourceCode(codeOrLabel);
  switch (code) {
    case 'ACTA':
      return SOURCE_TYPE_LABELS.EXCEL_ACTA;
    case 'MOODLE':
      return SOURCE_TYPE_LABELS.MOODLE_AULA;
    case 'COBRANZA':
      return SOURCE_TYPE_LABELS.SHEETS_COBRANZA;
    case 'ADMISION':
      return SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES;
    default:
      return '';
  }
}

/**
 * Indica si el tipo documental requiere selector de escala de calificación (#16)
 * Solo aplica a archivos académicos (ACTA y MOODLE).
 */
export function isAcademicSourceType(type) {
  const code = toCanonicalSourceCode(type);
  return code === 'ACTA' || code === 'MOODLE';
}

/**
 * Normaliza un texto eliminando tildes y convirtiendo a minúsculas para inspección de cabeceras
 */
function normalizeText(str) {
  return String(str || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Clasifica un conjunto de cabeceras / primeras filas de acuerdo con los patrones canónicos (#15)
 * @param {string[]} rawTokens
 * @returns {{ code: string, label: string, matchedKeywords: string[] }}
 */
export function classifyHeadersList(rawTokens = []) {
  const joined = rawTokens.map(normalizeText).join(' | ');
  if (!joined) {
    return { code: '', label: '', matchedKeywords: [] };
  }

  const cobranzaPatterns = [
    'monto_deuda', 'cuotas_impagas', 'monto_pagado', 'saldo_deuda',
    'cuotas en mora', 'concepto_pago', 'concepto financiero', 'deuda', 'mora', 'arancel', 'colegiatura'
  ];
  const moodlePatterns = [
    'idnumber', 'timemodified', 'finalgrade', 'course', 'itemid',
    'calificacion maxima', 'retroalimentacion', 'apellido(s)', 'direccion de correo'
  ];
  const admisionPatterns = [
    'marca temporal', 'timestamp', 'postulante', 'programa de interes',
    'medio de captacion', 'formulario de inscripcion', 'fecha_inscripcion'
  ];
  const actaPatterns = [
    'nota_final', 'calificacion', 'asistencia_pct', 'porcentaje_asistencia',
    'asistencia', 'nota final', 'promedio final', 'sigla_modulo', 'acta'
  ];

  const matchedCobranza = cobranzaPatterns.filter((kw) => joined.includes(kw));
  const matchedMoodle = moodlePatterns.filter((kw) => joined.includes(kw));
  const matchedAdmision = admisionPatterns.filter((kw) => joined.includes(kw));
  const matchedActa = actaPatterns.filter((kw) => joined.includes(kw));

  // Priorizar coincidencias específicas de cabeceras reales
  if (matchedCobranza.length >= 1 && matchedCobranza.length >= matchedActa.length) {
    return {
      code: 'COBRANZA',
      label: SOURCE_TYPE_LABELS.SHEETS_COBRANZA,
      matchedKeywords: matchedCobranza,
    };
  }
  if (matchedMoodle.length >= 1) {
    return {
      code: 'MOODLE',
      label: SOURCE_TYPE_LABELS.MOODLE_AULA,
      matchedKeywords: matchedMoodle,
    };
  }
  if (matchedAdmision.length >= 1) {
    return {
      code: 'ADMISION',
      label: SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES,
      matchedKeywords: matchedAdmision,
    };
  }
  if (matchedActa.length >= 1) {
    return {
      code: 'ACTA',
      label: SOURCE_TYPE_LABELS.EXCEL_ACTA,
      matchedKeywords: matchedActa,
    };
  }

  return { code: '', label: '', matchedKeywords: [] };
}

/**
 * Extrae cadenas XML (<t>...</t>) desde un archivo .xlsx (ZIP) en el navegador usando DecompressionStream
 */
async function extractXlsxHeaderStrings(file) {
  try {
    const buffer = await file.slice(0, Math.min(file.size, 512 * 1024)).arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    const decoder = new TextDecoder('utf-8', { fatal: false });
    const extractedStrings = [];

    let offset = 0;
    while (offset + 30 <= bytes.length) {
      const sig = view.getUint32(offset, true);
      if (sig !== 0x04034b50) {
        offset += 1;
        continue;
      }
      const compressionMethod = view.getUint16(offset + 8, true);
      const compressedSize = view.getUint32(offset + 18, true);
      const fileNameLen = view.getUint16(offset + 26, true);
      const extraLen = view.getUint16(offset + 28, true);
      const nameStart = offset + 30;
      const dataStart = nameStart + fileNameLen + extraLen;

      if (nameStart + fileNameLen > bytes.length) break;
      const entryName = decoder.decode(bytes.subarray(nameStart, nameStart + fileNameLen));

      const isTargetXml =
        entryName === 'xl/sharedStrings.xml' ||
        entryName === 'xl/worksheets/sheet1.xml';

      if (isTargetXml && dataStart < bytes.length) {
        const endPos = compressedSize > 0
          ? Math.min(bytes.length, dataStart + compressedSize)
          : Math.min(bytes.length, dataStart + 128 * 1024);
        const slice = bytes.subarray(dataStart, endPos);

        let xmlText = '';
        if (compressionMethod === 0) {
          xmlText = decoder.decode(slice);
        } else if (compressionMethod === 8 && typeof DecompressionStream !== 'undefined') {
          try {
            const ds = new DecompressionStream('deflate-raw');
            const writer = ds.writable.getWriter();
            writer.write(slice).catch(() => {});
            writer.close().catch(() => {});
            const reader = ds.readable.getReader();
            const chunks = [];
            let totalRead = 0;
            while (totalRead < 65536) {
              const { value, done } = await reader.read();
              if (done || !value) break;
              chunks.push(value);
              totalRead += value.length;
            }
            const merged = new Uint8Array(totalRead);
            let pos = 0;
            for (const c of chunks) {
              merged.set(c, pos);
              pos += c.length;
            }
            xmlText = decoder.decode(merged);
          } catch {
            // Ignorar errores de stream parcial
          }
        }

        if (xmlText) {
          const matches = xmlText.match(/<t[^>]*>([^<]+)<\/t>/gi) || [];
          for (const m of matches.slice(0, 60)) {
            const cleaned = m.replace(/<\/?t[^>]*>/gi, '').trim();
            if (cleaned) extractedStrings.push(cleaned);
          }
        }
      }

      offset = dataStart + (compressedSize > 0 ? compressedSize : 1);
    }

    return extractedStrings;
  } catch {
    return [];
  }
}

/**
 * Inspecciona de forma asíncrona las primeras 5 filas / cabeceras de columna reales del archivo (#15).
 * Nunca devuelve "Acta" por defecto si las cabeceras no coinciden con un patrón conocido.
 *
 * @param {File} file
 * @returns {Promise<{ sourceType: string, code: string, recognized: boolean, matchedKeywords: string[] }>}
 */
export async function inspectFileHeaders(file) {
  if (!file) {
    return { sourceType: '', code: '', recognized: false, matchedKeywords: [] };
  }

  const fileName = (file.name || '').toLowerCase().trim();
  const lastDot = fileName.lastIndexOf('.');
  const ext = lastDot !== -1 ? fileName.substring(lastDot) : '';

  let headerCandidates = [];

  if (ext === '.csv') {
    try {
      const sampleText = await file.slice(0, 8192).text();
      const firstLines = sampleText
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)
        .slice(0, 5);
      headerCandidates = firstLines;
    } catch {
      headerCandidates = [];
    }
  } else if (ext === '.xlsx') {
    headerCandidates = await extractXlsxHeaderStrings(file);
  } else if (ext === '.xls') {
    try {
      const buffer = await file.slice(0, Math.min(file.size, 65536)).arrayBuffer();
      const ascii = new TextDecoder('latin1').decode(new Uint8Array(buffer));
      const printable = ascii.match(/[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ ]{4,}/g) || [];
      headerCandidates = printable.slice(0, 80);
    } catch {
      headerCandidates = [];
    }
  }

  const headerClassification = classifyHeadersList(headerCandidates);
  if (headerClassification.code) {
    return {
      sourceType: headerClassification.label,
      code: headerClassification.code,
      recognized: true,
      matchedKeywords: headerClassification.matchedKeywords,
    };
  }

  // Fallback secundario solo si el nombre del archivo contiene un término inequívoco;
  // NUNCA asumir "Acta" solo por la extensión .xlsx/.csv
  const cleanFileName = normalizeText(fileName.replace(/\.[^.]+$/, ''));
  const nameClassification = classifyHeadersList([cleanFileName]);
  if (nameClassification.code) {
    return {
      sourceType: nameClassification.label,
      code: nameClassification.code,
      recognized: true,
      matchedKeywords: nameClassification.matchedKeywords,
    };
  }

  return {
    sourceType: '',
    code: '',
    recognized: false,
    matchedKeywords: [],
  };
}

/**
 * Clasificación síncrona sin fallback ciego a "Acta" (#15).
 * Si no reconoce un patrón explícito, devuelve '' para obligar selección manual.
 *
 * @param {File|string} file
 * @returns {string} Etiqueta del tipo documental o '' si no se reconoce
 */
export function detectSourceType(file) {
  if (!file) return '';
  const fileName = typeof file === 'string' ? file : (file.name || '');
  const cleanName = normalizeText(fileName.replace(/\.[^.]+$/, ''));

  if (['cobranza', 'cartera', 'cuotas', 'pagos', 'mora', 'deuda'].some((kw) => cleanName.includes(kw))) {
    return SOURCE_TYPE_LABELS.SHEETS_COBRANZA;
  }
  if (['moodle', 'grades', 'aula_virtual', 'aula virtual'].some((kw) => cleanName.includes(kw))) {
    return SOURCE_TYPE_LABELS.MOODLE_AULA;
  }
  if (['form', 'encuesta', 'respuestas', 'inscrip', 'admision', 'postulante'].some((kw) => cleanName.includes(kw))) {
    return SOURCE_TYPE_LABELS.FORMS_INSCRIPCIONES;
  }
  if (['acta', 'calif', 'notas', 'rendimiento'].some((kw) => cleanName.includes(kw))) {
    return SOURCE_TYPE_LABELS.EXCEL_ACTA;
  }

  // Nunca asumir "Acta" por defecto
  return '';
}

/**
 * Valida en cliente las reglas de seguridad de archivo (#18):
 * - Extensión estrictamente en .xlsx, .xls o .csv (rechaza .xml y otros)
 * - Tamaño <= 15 MB y > 0 bytes
 *
 * @param {File} file
 * @returns {{ valid: boolean, error: string|null }}
 */
export function validateFileSecurityClient(file) {
  if (!file) {
    return { valid: false, error: 'Archivo inválido.' };
  }
  const name = (file.name || '').trim();
  const lastDot = name.lastIndexOf('.');
  const ext = lastDot !== -1 ? name.substring(lastDot).toLowerCase() : '';

  if (ext === '.xml') {
    return {
      valid: false,
      error: `El formato XML ("${name}") no está permitido por seguridad. Exporte desde Moodle en formato .csv o .xlsx.`,
    };
  }

  if (!FORMATOS_PERMITIDOS.includes(ext)) {
    return {
      valid: false,
      error: `Extensión "${ext || 'desconocida'}" no permitida en "${name}". Solo se admiten ${FORMATOS_PERMITIDOS.join(', ')}.`,
    };
  }

  if (file.size === 0) {
    return {
      valid: false,
      error: `El archivo "${name}" está vacío (0 bytes).`,
    };
  }

  if (file.size > MAX_TAMANO_ARCHIVO_BYTES) {
    return {
      valid: false,
      error: `El archivo "${name}" (${formatFileSize(file.size)}) excede el límite máximo de ${MAX_TAMANO_ARCHIVO_MB} MB.`,
    };
  }

  return { valid: true, error: null };
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
  const code = toCanonicalSourceCode(type);
  switch (code) {
    case 'ACTA':
      return {
        bg: '#dcfce7',
        color: '#15803d',
        shortName: 'Excel Acta',
        extension: '.xlsx',
      };
    case 'ADMISION':
      return {
        bg: '#e0e7ff',
        color: '#4338ca',
        shortName: 'Google Forms',
        extension: '.csv',
      };
    case 'MOODLE':
      return {
        bg: '#ffedd5',
        color: '#c2410c',
        shortName: 'Moodle',
        extension: '.csv/.xlsx',
      };
    case 'COBRANZA':
      return {
        bg: '#fef3c7',
        color: '#b45309',
        shortName: 'Cartera Cobranza',
        extension: '.xlsx/.csv',
      };
    default:
      return {
        bg: '#fef3c7',
        color: '#b45309',
        shortName: 'Sin reconocer',
        extension: '',
      };
  }
}
