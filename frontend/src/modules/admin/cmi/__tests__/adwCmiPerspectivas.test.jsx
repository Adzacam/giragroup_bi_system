import fs from 'node:fs';
import path from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TarjetaKpi from '../scorecard/TarjetaKpi';
import DesglosePerspectiva from '../scorecard/DesglosePerspectiva';
import CmiDetalleKpi from '../CmiDetalleKpi';
import cmiApi from '../../../../api/cmiApi';

vi.mock('../../../../context/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}));

vi.mock('react-chartjs-2', () => ({
  Bar: ({ data }) => <div data-testid="chart-bar">{JSON.stringify(data?.labels || [])}</div>,
  Doughnut: ({ data }) => <div data-testid="chart-doughnut">{JSON.stringify(data?.labels || [])}</div>,
}));

function renderConQuery(ui, detalleMock) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (detalleMock) {
    qc.setQueryData(['cmi', 'persp-detalle', detalleMock.codigo, detalleMock.gestion], detalleMock);
  }
  return renderToStaticMarkup(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('ADW-B4 — CMI Perspectivas, n_respuestas, captación y cero hex sueltos', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('TarjetaKpi muestra n_respuestas cuando está presente y lo omite si es null', () => {
    const kpiConResp = {
      codigo: 'KPI-20',
      nombre: 'Satisfacción institucional',
      descripcion: 'Encuesta institucional',
      unidad: 'PCT',
      sentido: 'MAX',
      valor: 79.3,
      valor_anterior: 78.37,
      delta: 0.93,
      meta: 85,
      semaforo: 'AMBAR',
      tendencia: 'MEJORA',
      n_respuestas: 14342,
    };
    const htmlCon = renderToStaticMarkup(<TarjetaKpi kpi={kpiConResp} onAbrir={() => {}} forceClassicCard />);
    expect(htmlCon).toContain('14.342');
    expect(htmlCon).toContain('resp.');

    const kpiSinResp = { ...kpiConResp, codigo: 'KPI-01', n_respuestas: null };
    const htmlSin = renderToStaticMarkup(<TarjetaKpi kpi={kpiSinResp} onAbrir={() => {}} forceClassicCard />);
    expect(htmlSin).not.toContain('resp.');
  });

  it('CmiDetalleKpi muestra n_respuestas en la tabla histórica cuando está presente y lo omite si es null', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['cmi', 'historial', 'KPI-20'], {
      codigo: 'KPI-20',
      nombre: 'Satisfacción institucional',
      descripcion: 'Encuesta institucional',
      unidad: 'PCT',
      sentido: 'MAX',
      serie: [
        { gestion: 2024, valor: 79.71, meta: 85, semaforo: 'AMBAR', n_respuestas: 1091 },
        { gestion: 2025, valor: 78.37, meta: 85, semaforo: 'AMBAR', n_respuestas: 14342 },
      ],
    });
    const htmlCon = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiDetalleKpi codigo="KPI-20" onClose={() => {}} />
      </QueryClientProvider>
    );
    expect(htmlCon).toContain('14.342');
    expect(htmlCon).toContain('1.091');
    expect(htmlCon).toContain('resp.');

    const qcSin = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qcSin.setQueryData(['cmi', 'historial', 'KPI-01'], {
      codigo: 'KPI-01',
      nombre: 'Ticket promedio',
      descripcion: 'Ticket',
      unidad: 'BS',
      sentido: 'MAX',
      serie: [
        { gestion: 2024, valor: 1927, meta: null, semaforo: 'SIN_UMBRAL' },
        { gestion: 2025, valor: 3654, meta: null, semaforo: 'SIN_UMBRAL' },
      ],
    });
    const htmlSin = renderToStaticMarkup(
      <QueryClientProvider client={qcSin}>
        <CmiDetalleKpi codigo="KPI-01" onClose={() => {}} />
      </QueryClientProvider>
    );
    expect(htmlSin).not.toContain('resp.');
  });

  it('DesglosePerspectiva en CLIENTES usa captacion_mensual + captacion_cobertura y no conversion_fuente', () => {
    const perspClientes = {
      codigo: 'CLIENTES',
      nombre: 'Estudiantes y mercado',
      objetivo: 'Captación y retención',
      peso: 25,
      indice: 75,
      kpis: [],
    };
    const detalleClientes = {
      codigo: 'CLIENTES',
      gestion: 2026,
      series: {
        inscritos_programa: [{ programa: 'Diplomado BI', inscritos: 42 }],
        captacion_mensual: [
          { gestion: 2026, mes: 3, periodo_mes: '2026-03', leads: 120, inscritos: 36, programas: 4, conversion_pct: 30 },
        ],
        captacion_cobertura: [
          { gestion: 2026, meses_con_dato: 1, meses_gestion: 12, desde: 'marzo de 2026', hasta: 'marzo de 2026' },
        ],
      },
      kpis_personalizados: [],
      graficos_personalizados: [],
      avisos: [],
    };

    const html = renderConQuery(
      <DesglosePerspectiva perspectiva={perspClientes} gestion={2026} onVolver={() => {}} onAbrirKpi={() => {}} />,
      detalleClientes
    );
    expect(html).toContain('Captación mensual (leads vs. inscritos)');
    expect(html).toContain('Cobertura: 1 de 12 meses (marzo de 2026 a marzo de 2026)');
    expect(html).toContain('2026-03');
    expect(html).not.toContain('Captación por fuente');
    expect(html).not.toContain('Meta vs. ejecutado mensual');
    expect(html).not.toContain('Estudiantes en riesgo por nivel');
  });

  it('DesglosePerspectiva mantiene gráficas estrictamente alineadas a cada área', () => {
    const areas = [
      ['FINANCIERA', 'Meta vs. ejecutado mensual (Bs)', 'Inscritos por programa'],
      ['PROCESOS_INTERNOS', 'Documentos DataOps por fuente', 'Cartera por estado (Bs deuda)'],
      ['APRENDIZAJE', 'Estudiantes en riesgo por nivel', 'Documentos DataOps por fuente'],
    ];
    for (const [codigo, esperado, ajeno] of areas) {
      const html = renderConQuery(
        <DesglosePerspectiva
          perspectiva={{ codigo, nombre: codigo, objetivo: 'Obj', peso: 25, indice: 80, kpis: [] }}
          gestion={2026}
          onVolver={() => {}}
          onAbrirKpi={() => {}}
        />,
        { codigo, gestion: 2026, series: {}, kpis_personalizados: [], graficos_personalizados: [], avisos: [] }
      );
      expect(html).toContain(esperado);
      expect(html).not.toContain(ajeno);
    }
    expect(typeof cmiApi.getDetallePerspectiva).toBe('function');
  });

  it('Guardia: cero colores hex (#RRGGBB) sueltos en frontend/src/modules/admin/cmi/', () => {
    const cmiRoot = path.resolve(__dirname, '..');
    const encontrados = [];
    const recorrer = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.name === '__tests__') continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          recorrer(full);
        } else if (/\.(js|jsx|css)$/.test(entry.name)) {
          const text = fs.readFileSync(full, 'utf8');
          const matches = text.match(/#[0-9a-fA-F]{3,8}\b/g);
          if (matches) {
            encontrados.push({ file: path.relative(cmiRoot, full), matches });
          }
        }
      }
    };
    recorrer(cmiRoot);
    expect(encontrados).toEqual([]);
  });
});
