/**
 * Fallback mock data for DataOps and BI Governance views
 * Used gracefully when the backend or database is offline.
 */

export const MOCK_SOURCES = [
  {
    id: 1,
    name: 'Acta_POS_2026_Modulo3.xlsx',
    type: 'Excel Acta',
    records: 342,
    date: '2026-09-20 10:15',
    status: 'completed',
    sha256: '8f4e2a1b'
  },
  {
    id: 2,
    name: 'Respuestas_Encuesta_M3.csv',
    type: 'Google Forms',
    records: 215,
    date: '2026-09-19 14:30',
    status: 'completed',
    sha256: '3a9c1b2c'
  },
  {
    id: 3,
    name: 'Moodle_Grades_Export.xml',
    type: 'Aula Moodle',
    records: 691,
    date: '2026-09-18 09:45',
    status: 'warning',
    sha256: 'c5f2d84a'
  },
  {
    id: 4,
    name: 'Cartera_Cobranza_Sep2026.xlsx',
    type: 'Cartera de Cobranza (Sheets)',
    records: 412,
    date: '2026-09-17 11:20',
    status: 'completed',
    sha256: '7e3b9f01'
  }
];

export const MOCK_NORMALIZATION_MATRIX = [
  { o: 'NOMBRES Y APELLIDOS', n: 'nombre_completo', t: 'VARCHAR', r: 'Mapeo directo' },
  { o: 'CALIF_FINAL', n: 'nota_final', t: 'NUMERIC', r: 'Conversión a float' },
  { o: 'DOC_IDENTIDAD/CI', n: 'ci_estudiante', t: 'VARCHAR', r: 'Limpieza alfanumérica' },
  { o: 'COD_MODULO', n: 'codigo_modulo', t: 'VARCHAR', r: 'Mapeo directo' },
  { o: 'FECHA_EVAL', n: 'fecha_asentamiento', t: 'DATE', r: 'Parseo YYYY-MM-DD' },
  { o: 'OBSERVACIONES', n: 'observacion', t: 'TEXT', r: 'Sanitizado HTML' }
];

export const MOCK_INITIAL_LOGS = [
  { time: '10:15:02', type: 'INFO', module: 'dispatcher.py', msg: 'Iniciando pipeline para lote POS-2026-B_M3' },
  { time: '10:15:03', type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 completado (342 filas)' },
  { time: '10:15:04', type: 'INFO', module: 'cleaner.py', msg: 'Sanitizado de caracteres especiales finalizado' },
  { time: '10:15:05', type: 'INFO', module: 'mapper.py', msg: 'Mapeo de 12 columnas a esquema canónico' },
  { time: '10:15:06', type: 'WARN', module: 'validator.py', msg: '52 registros con inconsistencias estructurales detectados' },
  { time: '10:15:07', type: 'SUCCESS', module: 'pipeline.py', msg: '1,196 registros listos para staging' },
  { time: '10:15:08', type: 'INFO', module: 'loader.py', msg: 'Batch INSERT a esquema staging completado' },
  { time: '10:15:09', type: 'SUCCESS', module: 'pipeline.py', msg: 'Pipeline ejecutado con éxito en 4.2s' }
];
