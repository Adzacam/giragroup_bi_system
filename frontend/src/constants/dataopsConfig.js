/**
 * frontend/src/constants/dataopsConfig.js
 * ---------------------------------------
 * Constantes centralizadas de umbrales y reglas del flujo DataOps y BETO NER (#3, #6).
 */

/** Compuerta mínima de lectura base del modelo por entidad para poder recibir bonos (escala 0–1 y 0–100) */
export const COMPUERTA_LECTURA_MODELO = 0.70;
export const COMPUERTA_LECTURA_MODELO_PCT = 70;

/** Umbral de corte del índice final del registro para pase directo al Data Warehouse (escala 0–100 y 0–1) */
export const UMBRAL_INDICE_REGISTRO = 85;
export const UMBRAL_INDICE_REGISTRO_DEC = 0.85;

/** Tope máximo del índice por entidad tras aplicar bonos acumulativos */
export const TOPE_INDICE_BONIFICADO = 99;
export const TOPE_INDICE_BONIFICADO_DEC = 0.99;

/** Límites de seguridad para ingesta multi-archivo (#18) */
export const MAX_ARCHIVOS_POR_LOTE = 10;
export const MAX_TAMANO_ARCHIVO_MB = 15;
export const MAX_TAMANO_ARCHIVO_BYTES = MAX_TAMANO_ARCHIVO_MB * 1024 * 1024;
export const FORMATOS_PERMITIDOS = ['.xlsx', '.xls', '.csv'];

/** Escalas de calificación para archivos académicos (#16) */
export const ESCALAS_ACADEMICAS = [
  { value: 'CENTESIMAL_100', label: '0 – 100 pts (Centesimal)', factor: 1 },
  { value: 'DECIMAL_10', label: '0 – 10 pts (Decimal — Moodle)', factor: 10 },
  { value: 'VIGESIMAL_20', label: '0 – 20 pts (Vigesimal)', factor: 5 },
];

/** Tipos de fuente reconocidos (#8, #15) */
export const TIPOS_FUENTE_DATAOPS = [
  { code: 'ACTA', label: 'Acta de calificaciones', requiereEscala: true },
  { code: 'MOODLE', label: 'Reporte Aula Moodle', requiereEscala: true },
  { code: 'COBRANZA', label: 'Cobranza y pagos', requiereEscala: false },
  { code: 'ADMISION', label: 'Admisiones y matriculación', requiereEscala: false },
];
