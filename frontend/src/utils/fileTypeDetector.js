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
  TIPOS_FUENTE_DATAOPS,
} from '../constants/dataopsConfig.js';

export const SOURCE_TYPE_LABELS = {
  EXCEL_ACTA: 'Acta de calificaciones',
  FORMS_INSCRIPCIONES: 'Admisiones y matriculación',
  MOODLE_AULA: 'Reporte Aula Moodle',
  SHEETS_COBRANZA: 'Cobranza y pagos',
  EVALUACION_DOCENTE: 'Evaluación docente',
  EGRESOS: 'Egresos',
  TECHOS: 'Techos de convenio',
  RENTABILIDAD: 'Rentabilidad',
  MARKETING: 'Marketing',
  PLANIFICACION: 'Planificación',
};

export const SOURCE_TYPES = TIPOS_FUENTE_DATAOPS.map((t) => t.label);

export const UNRECOGNIZED_SOURCE_LABEL = 'Sin reconocer — Seleccione tipo documental';

const CANONICAL_CODES = new Set(TIPOS_FUENTE_DATAOPS.map((t) => t.code));

/**
 * Convierte cualquier etiqueta o código al código canónico de BD (10 tipos o '')
 */
export function toCanonicalSourceCode(type) {
  if (!type) return '';
  const raw = String(type).trim();
  const upper = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase();

  if (CANONICAL_CODES.has(upper)) {
    return upper;
  }
  const byLabel = TIPOS_FUENTE_DATAOPS.find(
    (t) =>
      t.label
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase() === upper
  );
  if (byLabel) return byLabel.code;

  if (upper.includes('MOODLE') || upper.includes('AULA VIRTUAL') || upper.includes('LMS')) {
    return 'MOODLE';
  }
  if (upper.includes('EVALUACION') || upper.includes('EXPERIENCIA DOCENTE') || upper.includes('ENCUESTA DOCENTE')) {
    return 'EVALUACION_DOCENTE';
  }
  if (upper.includes('EGRESO')) {
    return 'EGRESOS';
  }
  if (upper.includes('TECHO')) {
    return 'TECHOS';
  }
  if (upper.includes('RENTABILIDAD') || upper.includes('EBITDA') || upper.includes('EJECUTADO VS META')) {
    return 'RENTABILIDAD';
  }
  if (upper.includes('MARKETING') || upper.includes('LEAD') || upper.includes('CAMPANA')) {
    return 'MARKETING';
  }
  if (upper.includes('PLANIFICA') || upper.includes('CRONOGRAMA')) {
    return 'PLANIFICACION';
  }
  if (upper.includes('COBRANZA') || upper.includes('CARTERA') || upper.includes('PAGO')) {
    return 'COBRANZA';
  }
  if (upper.includes('INSCRIP') || upper.includes('ADMISION') || upper.includes('FORMS') || upper.includes('MATRICUL')) {
    return 'ADMISION';
  }
  if (upper.includes('ACTA') || upper.includes('CALIFIC')) {
    return 'ACTA';
  }
  return '';
}

/**
 * Convierte código canónico a la etiqueta legible del selector
 */
export function toSourceTypeLabel(codeOrLabel) {
  const code = toCanonicalSourceCode(codeOrLabel);
  if (!code) return '';
  return TIPOS_FUENTE_DATAOPS.find((t) => t.code === code)?.label || '';
}

/**
 * Indica si el tipo documental requiere selector de escala de calificación (#16, W-2)
 * Solo aplica a archivos académicos (ACTA y MOODLE).
 */
export function isAcademicSourceType(type) {
  const code = toCanonicalSourceCode(type);
  return TIPOS_FUENTE_DATAOPS.find((t) => t.code === code)?.requiereEscala === true;
}

/**
 * Decodifica entidades numéricas y nombradas XML/HTML (ej. &#211; -> Ó) y normaliza texto sin tildes
 */
function normalizeText(str) {
  const decoded = String(str || '')
    .replace(/&#(\d+);/g, (_, dec) => String.fromCharCode(Number(dec)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');

  return decoded
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
  const normalizedTokens = rawTokens.map(normalizeText).filter(Boolean);
  const joined = normalizedTokens.join(' | ');
  if (!joined) {
    return { code: '', label: '', matchedKeywords: [] };
  }

  const labelFor = (code) => toSourceTypeLabel(code) || code;

  const evaluacionPatterns = [
    'totalmente de acuerdo', 'totalmente en desacuerdo', 'muy de acuerdo',
    'nada satisfecho', 'escala de 1 a 5', 'escala del 1 al 10',
    'evaluacion docente', 'evaluacion_docente', 'evaluacion del docente',
    'experiencia docente', 'experiencia unifranz', 'tbl evaluacion docente',
    'tbl experiencia unifranz', 'entrada anonima - persona', 'entrada anonima',
    'docente explica', 'dominio sobre los temas', 'dominio del contenido',
    'fomenta la participacion', 'accesible y resuelve dudas',
    'satisfaccion general', 'probabilidad de recomendar',
    'respuesta numero', 'numero del modulo', 'recursos tecnologicos proporcionados',
    'personal administrativo fue receptivo',
  ];

  const egresosPatterns = [
    'egreso anterior', 'egreso real', 'bd egresos', 'comprobante de egreso',
    'desembolso', 'egresos', 'partida',
  ];

  const techosPatterns = [
    'gestion techo', 'escuela techo', 'bd techos', 'techo presupuestario',
    'techo convenio', 'techos',
  ];

  const rentabilidadPatterns = [
    'ejecutado vs meta', 'meta por categoria', 'ejecutado 202', 'ebitda',
    'rentabilidad', 'monto_ejecutado', 'monto_meta',
  ];

  const marketingPatterns = [
    'medio de captacion', 'fuente lead', 'leads', 'campana',
    'marketing', 'reservas',
  ];

  const planificacionPatterns = [
    'planificacion y ejecucion', 'planificacion_ejecucion', 'fecha de planificacion',
    'diseno curricular', 'coordinador academico', 'origen del programa',
    'tc (cliente externo)', 'centralizado_mensual', 'programas notificados',
    'cronograma', 'carga horaria', 'planificacion', 'ejecucion academica',
  ];

  const cobranzaPatterns = [
    'monto_deuda', 'cuotas_impagas', 'monto_pagado', 'saldo_deuda',
    'cuotas en mora', 'en mora', 'dias de mora', 'concepto_pago', 'concepto financiero',
    'deuda', 'arancel', 'colegiatura', 'bd cobranzas', 'cobranza',
    'estado de pago', 'fecha de la primera factura', 'cartera cerrada',
  ];

  const moodlePatterns = [
    'idnumber', 'id number', 'timemodified', 'finalgrade', 'itemid',
    'calificacion maxima', 'retroalimentacion', 'apellido(s)', 'grade/100',
    'last downloaded from this course', 'reporte_aula_virtual', 'aula virtual moodle',
    'aula_virtual_moodle', 'total del curso',
  ];

  const admisionPatterns = [
    'marca temporal', 'timestamp', 'postulante', 'programa de interes',
    'medio de contacto', 'formulario de inscripcion', 'fecha_inscripcion',
    'tipo de inscripcion', 'estado del inscrito', 'numeroproyecto', 'pos-ci inscritos',
    'pos-ci incritos', 'tbl_inscritos', 'inscripciones_google_forms', 'inscripciones',
    'bajas por duplicados',
  ];

  const actaPatterns = [
    'nota_final', 'calificacion', 'asistencia_pct', 'porcentaje_asistencia',
    'nota final', 'promedio final', 'sigla_modulo', 'acta', 'actas de notas',
    'pos - actas', 'estado academico', 'estado tutoria', 'estado arca',
    'fecha emision arca', 'base_academica', 'base centralizada academica',
    'modulo 1', 'modulo 2',
  ];

  const matchedEval = evaluacionPatterns.filter((kw) => joined.includes(kw));
  // Regla estructural de evaluación docente: "Programa" + "Módulo" numérico (sin nota/acta)
  const hasPrograma = normalizedTokens.some((t) => t === 'programa' || t.startsWith('programa ') || t.includes('programa pos') || t.includes('programa -'));
  const hasModulo = normalizedTokens.some((t) => t === 'modulo' || t === 'numero del modulo');
  const hasNumericModulo = normalizedTokens.some((t) => /^(?:1|2|3|4|5|6|7|8|9|10)(?:\.0)?$/.test(t));
  const hasNotaOActa = joined.includes('nota') || joined.includes('calificacion') || joined.includes('pos - actas');
  if (hasPrograma && hasModulo && (hasNumericModulo || joined.includes('nombre completo del usuario') || joined.includes('direccion de correo')) && !hasNotaOActa) {
    matchedEval.push('programa+modulo_numerico');
  }

  const matchedEgresos = egresosPatterns.filter((kw) => joined.includes(kw));
  const matchedTechos = techosPatterns.filter((kw) => joined.includes(kw));
  const matchedRent = rentabilidadPatterns.filter((kw) => joined.includes(kw));
  const matchedMkt = marketingPatterns.filter((kw) => joined.includes(kw));
  const matchedPlan = planificacionPatterns.filter((kw) => joined.includes(kw));
  const matchedCobranza = cobranzaPatterns.filter((kw) => joined.includes(kw));
  const matchedMoodle = moodlePatterns.filter((kw) => joined.includes(kw));
  const matchedAdmision = admisionPatterns.filter((kw) => joined.includes(kw));
  const matchedActa = actaPatterns.filter((kw) => joined.includes(kw));

  const candidates = [
    { code: 'EVALUACION_DOCENTE', label: labelFor('EVALUACION_DOCENTE'), matches: matchedEval },
    { code: 'TECHOS', label: labelFor('TECHOS'), matches: matchedTechos },
    { code: 'EGRESOS', label: labelFor('EGRESOS'), matches: matchedEgresos },
    { code: 'RENTABILIDAD', label: labelFor('RENTABILIDAD'), matches: matchedRent },
    { code: 'PLANIFICACION', label: labelFor('PLANIFICACION'), matches: matchedPlan },
    { code: 'MARKETING', label: labelFor('MARKETING'), matches: matchedMkt },
    { code: 'ADMISION', label: labelFor('ADMISION'), matches: matchedAdmision },
    { code: 'MOODLE', label: labelFor('MOODLE'), matches: matchedMoodle },
    { code: 'COBRANZA', label: labelFor('COBRANZA'), matches: matchedCobranza },
    { code: 'ACTA', label: labelFor('ACTA'), matches: matchedActa },
  ].filter((c) => c.matches.length >= 1);

  if (candidates.length > 0) {
    candidates.sort((a, b) => b.matches.length - a.matches.length);
    const winner = candidates[0];
    return {
      code: winner.code,
      label: winner.label,
      matchedKeywords: winner.matches,
    };
  }

  return { code: '', label: '', matchedKeywords: [] };
}

/**
 * Extrae cadenas XML (<t>...</t>) desde un archivo .xlsx (ZIP) en el navegador usando DecompressionStream
 */
async function extractXlsxHeaderStrings(file) {
  try {
    const buffer = await file.slice(0, Math.min(file.size, 6 * 1024 * 1024)).arrayBuffer();
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
        entryName === 'xl/worksheets/sheet1.xml' ||
        entryName === 'xl/workbook.xml';

      if (isTargetXml && dataStart < bytes.length) {
        const endPos = compressedSize > 0
          ? Math.min(bytes.length, dataStart + compressedSize)
          : Math.min(bytes.length, dataStart + 256 * 1024);
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
            while (totalRead < 98304) {
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
          for (const m of matches.slice(0, 80)) {
            const cleaned = m.replace(/<\/?t[^>]*>/gi, '').trim();
            if (cleaned) extractedStrings.push(cleaned);
          }
          const sheetMatches = xmlText.match(/<sheet[^>]+name="([^"]+)"/gi) || [];
          for (const sm of sheetMatches) {
            const nameMatch = sm.match(/name="([^"]+)"/i);
            if (nameMatch && nameMatch[1]) extractedStrings.push(nameMatch[1]);
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

  const cleanFileName = normalizeText(fileName.replace(/\.[^.]+$/, ''));
  const headerClassification = classifyHeadersList([...headerCandidates, cleanFileName]);
  if (headerClassification.code) {
    return {
      sourceType: headerClassification.label,
      code: headerClassification.code,
      recognized: true,
      matchedKeywords: headerClassification.matchedKeywords,
    };
  }

  const fallbackLabel = detectSourceType(fileName);
  const fallbackCode = toCanonicalSourceCode(fallbackLabel);
  if (fallbackCode) {
    return {
      sourceType: fallbackLabel,
      code: fallbackCode,
      recognized: true,
      matchedKeywords: [cleanFileName],
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

  if (['evaluacion', 'experiencia docente', 'experiencia', 'nps'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('EVALUACION_DOCENTE');
  }
  if (['egreso', 'egresos', 'gasto'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('EGRESOS');
  }
  if (['techo', 'techos'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('TECHOS');
  }
  if (['rentabilidad', 'ejecutado', 'ebitda'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('RENTABILIDAD');
  }
  if (['marketing', 'lead', 'campana'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('MARKETING');
  }
  if (['planificacion', 'cronograma'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('PLANIFICACION');
  }
  if (['cobranza', 'cartera', 'cuotas', 'pagos', 'mora', 'deuda'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('COBRANZA');
  }
  if (['moodle', 'grades', 'aula_virtual', 'aula virtual'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('MOODLE');
  }
  if (['form', 'inscrip', 'admision', 'postulante', 'tbl_inscritos'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('ADMISION');
  }
  if (['acta', 'calif', 'notas', 'rendimiento', 'arca'].some((kw) => cleanName.includes(kw))) {
    return toSourceTypeLabel('ACTA');
  }

  // Nunca asumir "Acta" por defecto
  return '';
}

/**
 * Valida en cliente las reglas de seguridad de archivo (#18):
 * - Extensión estrictamente en .xlsx, .xls o .csv (rechaza .xml y otros)
 * - Tamaño <= MAX_TAMANO_ARCHIVO_MB y > 0 bytes
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
        shortName: 'Cobranza y pagos',
        extension: '.xlsx/.csv',
      };
    case 'EVALUACION_DOCENTE':
      return {
        bg: '#f3e8ff',
        color: '#6b21a8',
        shortName: 'Evaluación docente',
        extension: '.xlsx',
      };
    case 'EGRESOS':
      return {
        bg: '#fee2e2',
        color: '#b91c1c',
        shortName: 'Egresos',
        extension: '.xlsx',
      };
    case 'TECHOS':
      return {
        bg: '#e0f2fe',
        color: '#0369a1',
        shortName: 'Techos de convenio',
        extension: '.xlsx',
      };
    case 'RENTABILIDAD':
      return {
        bg: '#dcfce7',
        color: '#166534',
        shortName: 'Rentabilidad',
        extension: '.xlsx',
      };
    case 'MARKETING':
      return {
        bg: '#fce7f3',
        color: '#be185d',
        shortName: 'Marketing',
        extension: '.xlsx/.csv',
      };
    case 'PLANIFICACION':
      return {
        bg: '#f1f5f9',
        color: '#334155',
        shortName: 'Planificación',
        extension: '.xlsx',
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
