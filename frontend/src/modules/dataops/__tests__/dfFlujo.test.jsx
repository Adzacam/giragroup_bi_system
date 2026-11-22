import { describe, it, expect } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import SystemCapabilitiesStrip from '../components/SystemCapabilitiesStrip';
import EntityHighlightText from '../components/EntityHighlightText';
import ReviewActionRenderer from '../components/ReviewActionRenderer';

describe('PLAN_DATAOPS_FLUJO — Capacidades, IOB2 y Renderizador genérico', () => {
  it('DF-L6: SystemCapabilitiesStrip renderiza las tarjetas de los 3 pasos sin números de tarea', () => {
    for (const step of [1, 2, 3]) {
      const html = renderToStaticMarkup(<SystemCapabilitiesStrip step={step} />);
      expect(html).toContain('Qué hizo el sistema en este paso');
      expect(html).not.toMatch(/tarea\s*\d/i);
    }
  });

  it('DF-L4: EntityHighlightText resalta spans beto_ents IOB2 con tipo y confianza', () => {
    const html = renderToStaticMarkup(
      <EntityHighlightText
        text="Estudiante Juan Perez en Gestion Financiera"
        betoEnts={[
          { tipo: 'PER_ESTUDIANTE', texto: 'Juan Perez', start: 11, end: 21, score: 0.94 },
          { tipo: 'MODULO', texto: 'Gestion Financiera', start: 25, end: 43, score: 0.89 },
        ]}
      />
    );
    expect(html).toContain('PER_ESTUDIANTE 94%');
    expect(html).toContain('MODULO 89%');
  });

  it('DF-L3: ReviewActionRenderer renderiza CandidateSelector con candidatos clicables sin hardcodear motivo', () => {
    const html = renderToStaticMarkup(
      <ReviewActionRenderer
        item={{
          id: 99,
          candidatos: [
            { id_estudiante: 12, nombre: '••••', ci_enmascarada: '12••••78', programa: 'POS-5308', similitud: 92.5, probabilidad_beto: null },
          ],
          acciones: [
            {
              codigo: 'VINCULAR_CANDIDATO',
              etiqueta: 'Vincular al candidato seleccionado',
              widget: 'CandidateSelector',
              campos: [{ name: 'id_estudiante_candidato', label: 'Candidato seleccionado', type: 'candidate', required: true }],
              precarga: {},
            },
          ],
        }}
        onExecute={() => {}}
      />
    );
    expect(html).toContain('Vincular al candidato seleccionado');
    expect(html).toContain('Similitud 92.5 %');
    expect(html).toContain('POS-5308');
  });
});
