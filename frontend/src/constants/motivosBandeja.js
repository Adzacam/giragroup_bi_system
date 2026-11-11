/**
 * Textos legibles de los motivos de la bandeja HITL, de la fuente de resolución de cada entidad y del estado de vínculo (fk_estado).
 */
export const MOTIVOS_BANDEJA = {
  CI_NOMBRE_DISCORDANTE: 'La cédula coincide pero el nombre es distinto',
  CI_NOMBRE_VARIANTE: 'Misma cédula con otra escritura del nombre (resuelto automáticamente)',
  HOMONIMIA: 'Posible homonimia: nombre parecido a otra persona',
  BAJA_CONFIANZA_IA: 'Lectura con baja confianza',
  BAJA_CONFIANZA: 'Lectura con baja confianza',
  LINEAS_NO_APLICABLES: 'Líneas sin hecho posible (numeración, títulos o casillas)',
  LIMITACION_FUENTE: 'Limitación de la fuente: el archivo no trae el dato',
  TIEMPO_IMPUTADO: 'Fecha imputada: el archivo no trae la fecha',
  HECHO_EN_REVISION: 'Hecho cargado que necesita revisión',
  ESTADO_FUERA_DE_CATALOGO: 'Estado fuera del catálogo',
  COMBINACION_INVALIDA: 'Combinación de estados no admitida',
  CI_DUDOSA: 'Cédula dudosa',
  CI_ILEGIBLE: 'Cédula ilegible',
  NOTA_FUERA_ESCALA: 'Nota fuera de escala',
  NOTA_INVALIDA: 'Nota inválida',
  ESCALA_AMBIGUA: 'Escala no declarada',
  ENTIDAD_NUEVA: 'Entidad nueva',
  REVISION_GENERAL: 'Revisión general',
  DOCENTE_SIN_VINCULAR: 'Docente sin vincular en la fuente',
};

export const textoMotivo = (motivo, etiquetaServidor) =>
  MOTIVOS_BANDEJA[String(motivo || '').toUpperCase()] || etiquetaServidor || String(motivo || '').replace(/_/g, ' ').toLowerCase();

export const FUENTES_RESOLUCION = {
  CI_EXACTA: 'Cédula exacta',
  FUZZY: 'Parecido de nombre (RapidFuzz)',
  ENCABEZADO: 'Encabezado de la columna',
  REGEX: 'Patrón de texto',
  BETO: 'Modelo BETO',
};

export const textoFuente = (f) => FUENTES_RESOLUCION[String(f || '').toUpperCase()] || (f ? String(f) : 'Sin determinar');

/** Estado de vínculo del estudiante (fk_estado): leyenda y filtros. */
export const ESTADOS_VINCULO = [
  { codigo: 'A', texto: 'A · Cédula exacta' },
  { codigo: 'B', texto: 'B · Vinculado sin cédula exacta' },
  { codigo: 'C', texto: 'C · Sin vincular (en staging)' },
];

const ACCIONES = { APROBAR: 'Aprobar grupo', MAPEAR_ESTADO: 'Mapear a estado canónico', CORREGIR_FECHA: 'Corregir fecha', MANUAL: 'Revisar caso a caso' };
export const textoAccion = (a) => ACCIONES[a] || ACCIONES.APROBAR;

export const maskCi = (ci) => {
  if (!ci) return '—';
  const str = String(ci).trim();
  if (str.length <= 4) return '***';
  return `${str.slice(0, 2)}***${str.slice(-2)}`;
};

export const maskNombre = (nombre) => {
  if (!nombre) return 'Estudiante Anonimizado';
  const parts = String(nombre).trim().split(/\s+/);
  if (parts.length === 1) return `${parts[0][0]}.***`;
  return parts.map((p) => (p ? `${p[0]}.` : '')).join(' ') + ' (Anonimizado)';
};

export const maskTexto = (t) => {
  if (!t) return '';
  return String(t)
    .replace(/CI:\s*([0-9A-Za-z\-]+)/gi, (m, ci) => `CI: ${maskCi(ci)}`)
    .replace(/Nombre:\s*([^()|]+)/gi, (m, nom) => `Nombre: ${maskNombre(nom)}`)
    .replace(/Discordante con:\s*([^()|]+)/gi, (m, nom) => `Discordante con: ${maskNombre(nom)}`)
    .replace(/\b\d{6,10}\b/g, (m) => maskCi(m));
};

const FALTAN = { estudiante: 'estudiante', modulo: 'módulo', nota: 'nota', fecha: 'fecha', monto: 'monto' };

/** Descripción legible del valor normalizado de un grupo (los de hechos traen documento, campos faltantes y estados). */
export function describirGrupo(g) {
  if (!g) return '';
  if (g.motivo === 'CI_NOMBRE_DISCORDANTE') {
    return `Cédula: ${maskCi(g.valor)}`;
  }
  if (g.motivo === 'HOMONIMIA') {
    return `Candidato: ${maskNombre(g.valor)}`;
  }
  if (g.motivo !== 'HECHO_EN_REVISION') {
    return maskTexto(g.valor);
  }
  const p = String(g.valor).split('|');
  const area = p[0] === 'academico' ? 'Académico' : 'Financiero';
  const doc = (p[1] || '').replace('doc', 'documento ');
  const faltan = (p[2] || '').replace('falta:', '');
  const falta = faltan === 'ninguno' ? 'campos completos' : `falta ${faltan.split(',').map((f) => FALTAN[f] || f).join(', ')}`;
  if (p[0] !== 'academico') return `${area} · ${doc} · ${falta}`;
  const estados = `${p[3]} / ${p[4]} / ${p[5]}`;
  const motivoEstado = (p[6] || '').replace('estado:', '');
  return `${area} · ${doc} · ${falta} · estados ${estados}${motivoEstado && motivoEstado !== 'OK' ? ` (${textoMotivo(motivoEstado)})` : ''}`;
}
