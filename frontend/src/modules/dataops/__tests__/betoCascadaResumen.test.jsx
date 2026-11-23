import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import BetoCascadaResumen from '../components/BetoCascadaResumen';
import ReviewActionRenderer from '../components/ReviewActionRenderer';
import CasoDetallePanel from '../components/CasoDetallePanel';

describe('BA-L4 — BetoCascadaResumen honesto (flags ON y OFF)', () => {
  it('muestra las 3 cifras separadas cuando los flags están activos', () => {
    const html = renderToStaticMarkup(
      <BetoCascadaResumen
        cascada={{
          total_entidades: 268091,
          lineas_confianza_beto: 76399,
          beto_aceptadas: 342,
          beto_leidas: 1200,
          acuerdo_qc_pct: 96.4,
          flags: { BETO_CASCADA_FINAL: true, BETO_ACUERDO_QC: true },
          etapas: [
            { etapa: 'CI_EXACTA', cantidad: 66598, porcentaje: 24.8 },
            { etapa: 'ENCABEZADO', cantidad: 125132, porcentaje: 46.7 },
            { etapa: 'FUZZY', cantidad: 31407, porcentaje: 11.7 },
            { etapa: 'REGEX', cantidad: 44612, porcentaje: 16.6 },
            { etapa: 'BETO', cantidad: 342, porcentaje: 0.1 },
          ],
        }}
      />
    );
    expect(html).toContain('BETO calculó la confianza de');
    expect(html).toContain('76');
    expect(html).toContain('BETO resolvió');
    expect(html).toContain('342');
    expect(html).toContain('BETO coincidió con las reglas en');
    expect(html).toContain('96.4 %');
  });

  it('dice explícitamente que la etapa está desactivada cuando los flags están apagados', () => {
    const html = renderToStaticMarkup(
      <BetoCascadaResumen
        cascada={{
          total_entidades: 268091,
          lineas_confianza_beto: 76399,
          beto_aceptadas: 0,
          beto_leidas: 0,
          acuerdo_qc_pct: null,
          flags: { BETO_CASCADA_FINAL: false, BETO_ACUERDO_QC: false },
          etapas: [
            { etapa: 'CI_EXACTA', cantidad: 66598, porcentaje: 24.8 },
            { etapa: 'ENCABEZADO', cantidad: 125132, porcentaje: 46.7 },
            { etapa: 'FUZZY', cantidad: 31407, porcentaje: 11.7 },
            { etapa: 'REGEX', cantidad: 44954, porcentaje: 16.8 },
            { etapa: 'BETO', cantidad: 0, porcentaje: 0.0 },
          ],
        }}
      />
    );
    const matches = html.match(/Esta etapa está desactivada por configuración/g) || [];
    expect(matches).toHaveLength(2);
  });

  it('renderiza candidatos con probabilidad BETO, ci_enmascarado y similitud 0..1 formateada', () => {
    const html = renderToStaticMarkup(
      <ReviewActionRenderer
        item={{
          id: 99,
          motivo: 'DESACUERDO_REGLA_BETO',
          sugerencias_beto: [
            { id: 7, nombre: '••••', ci_enmascarado: '12••••89', programa: 'POS-5252', similitud: 0.925, probabilidad_beto: 0.91 },
          ],
          candidatos: [
            { id: 7, nombre: '••••', ci_enmascarado: '12••••89', programa: 'POS-5252', similitud: 0.925, probabilidad_beto: 0.91 },
          ],
          acciones: [
            { codigo: 'VINCULAR_ESTUDIANTE', etiqueta: 'Vincular', widget: 'StudentSearch', campos: [] },
          ],
        }}
        onExecute={() => {}}
      />
    );
    expect(html).toContain('12••••89');
    expect(html).toContain('Similitud 92.5 %');
    expect(html).toContain('Probabilidad BETO 91 %');
  });

  it('muestra prioridad y detalle de regla en CasoDetallePanel para RELACION_INCOHERENTE', () => {
    const html = renderToStaticMarkup(
      <CasoDetallePanel
        item={{
          id: 101,
          motivo: 'RELACION_INCOHERENTE',
          prioridad: 'ALTA',
          regla_relacion: 'MODULO_EN_PROGRAMA',
          valor_relacion: 'POS-5252 · Mód. 9',
          detalle_relacion: 'El módulo 9 no existe para el programa POS-5252.',
          acciones: [],
        }}
        schedule={() => {}}
      />
    );
    expect(html).toContain('Prioridad ALTA');
    expect(html).toContain('MODULO_EN_PROGRAMA');
    expect(html).toContain('POS-5252 · Mód. 9');
  });
});
