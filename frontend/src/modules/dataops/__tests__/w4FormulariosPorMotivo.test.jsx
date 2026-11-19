import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { CasoRevision } from '../HumanReviewFlowView';

const MATRIZ = [
  {
    area: 'academica',
    motivo: 'CI_NOMBRE_DISCORDANTE',
    motivo_detalle: 'La CI 12••••78 coincide con una persona del catálogo, pero el nombre difiere.',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'ci_opcional', label: 'Cédula (opcional)', type: 'text', required: false },
      { name: 'confirmar_identidad', label: 'Confirmar identidad', type: 'select', required: true, options: ['Sí, es la misma persona', 'No, es otra persona'] },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"', 'name="gestion"'],
  },
  {
    area: 'academica',
    motivo: 'BAJA_CONFIANZA_IA',
    motivo_detalle: 'Índice probabilístico BETO (0,72) en la banda de revisión [0,60; 0,85).',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'modulo_resuelto', label: 'Módulo', type: 'text', required: true },
      { name: 'nota_final', label: 'Nota sobre 100', type: 'number', required: true },
      { name: 'mes', label: 'Mes', type: 'number', required: true },
      { name: 'gestion', label: 'Gestión', type: 'number', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="monto_deuda"', 'name="docente_resuelto"'],
  },
  {
    area: 'academica',
    motivo: 'HOMONIMIA',
    motivo_detalle: 'Dos personas con nombre similar (>90 %) en POS-5308, sin CI.',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'ci_opcional', label: 'Cédula (opcional)', type: 'text', required: false },
      { name: 'programa', label: 'Programa', type: 'text', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"', 'name="gestion"'],
  },
  {
    area: 'academica',
    motivo: 'CI_DUDOSA',
    motivo_detalle: 'CI con formato inválido o dudoso (12?4).',
    campos_correccion: [
      { name: 'ci_corregido', label: 'Cédula corregida', type: 'text', required: true },
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"'],
  },
  {
    area: 'evaluacion_docente',
    motivo: 'BAJA_CONFIANZA_IA',
    motivo_detalle: 'Índice probabilístico BETO (0,71) en respuestas Likert en POS-5252.',
    campos_correccion: [
      { name: 'programa', label: 'Programa', type: 'text', required: true },
      { name: 'numero_modulo', label: 'Número de módulo', type: 'number', required: true },
      { name: 'docente_resuelto', label: 'Docente', type: 'text', required: true },
      { name: 'escala_respuesta', label: 'Escala de respuesta', type: 'select', required: true, options: ['1 a 5', '1 a 10'] },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"', 'name="gestion"'],
  },
  {
    area: 'evaluacion_docente',
    motivo: 'HOMONIMIA',
    motivo_detalle: 'Otra persona con el mismo nombre en POS-5308, sin CI.',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'ci_opcional', label: 'Cédula (opcional)', type: 'text', required: false },
      { name: 'programa', label: 'Programa', type: 'text', required: true },
      { name: 'numero_modulo', label: 'Número de módulo', type: 'number', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"', 'name="gestion"'],
  },
  {
    area: 'comercial',
    motivo: 'POS_NO_EN_DIM_MODULO',
    motivo_detalle: "Código POS 'POS-9999' no encontrado en dim_modulo.",
    campos_correccion: [
      { name: 'codigo_pos', label: 'Código POS', type: 'text', required: true },
      { name: 'programa_resuelto', label: 'Programa', type: 'text', required: true },
      { name: 'modulo_resuelto', label: 'Módulo', type: 'text', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="nombre_completo"'],
  },
  {
    area: 'comercial',
    motivo: 'CI_DUDOSA',
    motivo_detalle: 'CI con formato inválido en TBL_INSCRITOS.',
    campos_correccion: [
      { name: 'ci_corregido', label: 'Cédula corregida', type: 'text', required: true },
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="monto_deuda"'],
  },
  {
    area: 'comercial',
    motivo: 'FECHA_INSCRIPCION_INVALIDA',
    motivo_detalle: 'Fecha de inscripción nula o fuera de rango en admisión.',
    campos_correccion: [
      { name: 'fecha_inscripcion', label: 'Fecha de inscripción', type: 'date', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="nombre_completo"', 'name="mes"'],
  },
  {
    area: 'financiera',
    motivo: 'CI_DUDOSA',
    motivo_detalle: 'CI con formato inválido en BD Cobranzas.',
    campos_correccion: [
      { name: 'ci_corregido', label: 'Cédula corregida', type: 'text', required: true },
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'monto_deuda', label: 'Monto de deuda', type: 'number', required: true },
      { name: 'cuotas_impagas', label: 'Cuotas impagas', type: 'number', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="docente_resuelto"'],
  },
  {
    area: 'financiera',
    motivo: 'CI_NOMBRE_DISCORDANTE',
    motivo_detalle: 'Discordancia de nombre/CI en BD Egresos.',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'ci_opcional', label: 'Cédula (opcional)', type: 'text', required: false },
      { name: 'categoria_financiera', label: 'Categoría financiera', type: 'text', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="cuotas_impagas"'],
  },
  {
    area: 'financiera',
    motivo: 'HOMONIMIA',
    motivo_detalle: 'Posible homonimia en BD Egresos, sin CI.',
    campos_correccion: [
      { name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true },
      { name: 'ci_opcional', label: 'Cédula (opcional)', type: 'text', required: false },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="mes"', 'name="gestion"'],
  },
  {
    area: 'comercial',
    motivo: 'TECHO_CONVENIO',
    motivo_detalle: 'Convenio o institución (Universidad X) por validar en techos de marketing.',
    campos_correccion: [
      { name: 'institucion', label: 'Institución', type: 'text', required: true },
      { name: 'clave_convenio', label: 'Clave de convenio', type: 'text', required: true },
      { name: 'monto_convenio', label: 'Monto de convenio', type: 'number', required: true },
      { name: 'justificacion', label: 'Justificación', type: 'text', required: true },
    ],
    prohibidos: ['name="nota_final"', 'name="nombre_completo"'],
  },
];

const decodeHtml = (s) =>
  s.replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');

describe('W-4 — Formularios dinámicos por motivo × categoría (V1 y V2)', () => {
  it.each(MATRIZ)(
    'renderiza solo los campos de $area / $motivo y muestra motivo_detalle',
    (caso) => {
      const item = {
        id: 101,
        area: caso.area,
        motivo: caso.motivo,
        motivo_detalle: caso.motivo_detalle,
        campos_correccion: caso.campos_correccion,
        estudiante: 'Ana Prueba',
        ci_enmascarado: '12••••78',
        archivo_origen: 'prueba.xlsx',
        indice_registro: 74,
        estado_resolucion: 'PENDIENTE',
      };

      const html = renderToStaticMarkup(
        <CasoRevision item={item} readOnly={false} busy={false} schedule={vi.fn()} />
      );

      expect(decodeHtml(html)).toContain(caso.motivo_detalle);
      for (const campo of caso.campos_correccion) {
        expect(html).toContain(`name="${campo.name}"`);
        expect(html).toContain(campo.label);
        if (campo.options) {
          for (const opt of campo.options) expect(html).toContain(opt);
        }
      }
      for (const prohibido of caso.prohibidos) {
        expect(html).not.toContain(prohibido);
      }
    }
  );
});
