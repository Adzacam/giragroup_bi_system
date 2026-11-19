import { describe, it, expect } from 'vitest';
import {
  TIPOS_FUENTE_DATAOPS,
  getTipoFuenteLabel,
} from '../../../constants/dataopsConfig';
import {
  classifyHeadersList,
  isAcademicSourceType,
  toCanonicalSourceCode,
  toSourceTypeLabel,
} from '../../../utils/fileTypeDetector';

const DIEZ_LIBROS_REALES = [
  {
    archivo: '[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx',
    esperado: 'EVALUACION_DOCENTE',
    tokens: [
      'Nombre Completo',
      'Grupos',
      'Dirección de correo',
      'Fecha',
      'Programa',
      'Módulo',
      '1. ¿La/El docente explica los conceptos de manera clara y comprensible?',
      '5/Totalmente de acuerdo',
      'ENTRADA ANONIMA - PERSONA 1',
      '1.0',
    ],
  },
  {
    archivo: 'Evaluación Docente y Unifranz.xlsx',
    esperado: 'EVALUACION_DOCENTE',
    tokens: [
      'Nombre completo del usuario',
      'Grupos',
      'Dirección de correo',
      'Fecha',
      'Programa - POS',
      'Número del modulo',
      'El contenido del módulo fue pertinente y se relaciona con los desafíos actuales del campo profesional.',
      'Bloque 5. Evaluación Global Por favor, responda las siguientes preguntas en una escala del 1 al 10.',
    ],
  },
  {
    archivo: 'Experiencia Docente 2.0.xlsx',
    esperado: 'EVALUACION_DOCENTE',
    tokens: [
      'N°',
      'Nombre completo del usuario',
      'Grupos',
      'Dirección de correo',
      'Fecha',
      'Programa POS',
      'Módulo',
      '1.0',
      'A 1. ¿La/El docente explica los conceptos de manera clara y comprensible?',
      '5/Totalmente de acuerdo',
    ],
  },
  {
    archivo: 'Base centralizada Académica ARCA (1).xlsx',
    esperado: 'ACTA',
    tokens: [
      'N°',
      'POS - ACTAS',
      'CÉDULA DE IDENTIDAD',
      'MES INICO',
      'AÑO INCIO',
      'APELLIDO PATERNO',
      'APELLIDO MATERNO',
      'NOMBRES',
      'MÓDULO 1',
      'MÓDULO 2',
    ],
  },
  {
    archivo: 'BD Cobranzas.xlsx',
    esperado: 'COBRANZA',
    tokens: [
      'TIPO DE PROGRAMA',
      'FECHA DE LA PRIMERA FACTURA',
      'POS',
      'NOMBRE DEL PROGRAMA',
      'ASESOR',
      'CI',
      'NOMBRES',
      'PATERNO',
      'MATERNO',
      'BD Cobranzas',
    ],
  },
  {
    archivo: 'TBL_INSCRITOS.xlsx',
    esperado: 'ADMISION',
    tokens: [
      'MARCA TEMPORAL',
      'NUMEROPROYECTO',
      'NOMBRE DEL PROGRAMA',
      'ASESOR',
      'CI',
      'NOMBRES',
      'PATERNO',
      'MATERNO',
      'CELULAR',
      'CORREO ELECTRONICO',
    ],
  },
  {
    archivo: 'BD Egresos.xlsx',
    esperado: 'EGRESOS',
    tokens: [
      'PROGRAMA',
      'EGRESO ANTERIOR',
      'EGRESO REAL',
      'INGRESO',
      'RENTABILIDAD',
      'NOMBRE DEL PROGRAMA',
      'TIPO DE PROGRAMA',
      'ESTADO DEL PROGRAMA',
      'NRO POS',
    ],
  },
  {
    archivo: 'BD Techos.xlsx',
    esperado: 'TECHOS',
    tokens: [
      'N°',
      'Gestión Techo',
      'Coord.',
      'Asistente',
      'Asesor Comercial',
      'Fecha Inicio',
      'Fecha Conclusión',
      'Escuela techo',
      'Insitución',
      'POS',
    ],
  },
  {
    archivo: 'EJECUTADO VS META.xlsx',
    esperado: 'RENTABILIDAD',
    tokens: [
      'CATEGORIA',
      'MES',
      'MES NUMERICO',
      'EJECUTADO 2023',
      'META POR CATEGORIA 2024',
      'EJECUTADO 2024',
      'EJECUTADO 2025',
      'META POR CATEGORIA 2025',
      'EJECUTADO 2026',
    ],
  },
  {
    archivo: 'PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx',
    esperado: 'PLANIFICACION',
    tokens: [
      'Nº',
      'FECHA',
      'AÑO',
      'MES',
      'NOMBRE MES',
      'TIPO DE PROGRAMA',
      'ESCUELA',
      'ORIGEN DEL PROGRAMA',
      'DISEÑO CURRICULAR',
      'TC (Cliente Externo)',
    ],
  },
];

describe('W-2 — Tipo documental en la SPA (D-W1)', () => {
  it('incluye los 10 códigos del backend con etiquetas llanas y requiereEscala solo en ACTA y MOODLE', () => {
    const codigos = TIPOS_FUENTE_DATAOPS.map((t) => t.code);
    expect(codigos).toEqual([
      'ACTA',
      'MOODLE',
      'COBRANZA',
      'ADMISION',
      'EVALUACION_DOCENTE',
      'EGRESOS',
      'TECHOS',
      'RENTABILIDAD',
      'MARKETING',
      'PLANIFICACION',
    ]);

    for (const tf of TIPOS_FUENTE_DATAOPS) {
      expect(tf.label).toBeTruthy();
      expect(getTipoFuenteLabel(tf.code)).toBe(tf.label);
      expect(toSourceTypeLabel(tf.code)).toBe(tf.label);
      expect(toCanonicalSourceCode(tf.label)).toBe(tf.code);
      expect(tf.requiereEscala).toBe(tf.code === 'ACTA' || tf.code === 'MOODLE');
      expect(isAcademicSourceType(tf.code)).toBe(tf.code === 'ACTA' || tf.code === 'MOODLE');
    }
  });

  it('clasifica correctamente los encabezados reales de los 10 libros (10/10)', () => {
    for (const libro of DIEZ_LIBROS_REALES) {
      const res = classifyHeadersList(libro.tokens);
      expect(res.code, `Falló ${libro.archivo}`).toBe(libro.esperado);
    }
  });

  it('reconoce evaluación docente por Programa + Módulo numérico sin selector de escala', () => {
    const res = classifyHeadersList(['Nombre completo del usuario', 'Programa', 'Módulo', '1.0']);
    expect(res.code).toBe('EVALUACION_DOCENTE');
    expect(isAcademicSourceType(res.code)).toBe(false);
  });
});
