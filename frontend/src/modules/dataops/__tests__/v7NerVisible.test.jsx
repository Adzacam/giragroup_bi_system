import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BetoReadingFlowView from '../BetoReadingFlowView';
import { NotificationProvider } from '../../../context/NotificationContext';

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { correo: 'test@giragroup.com', rol: 'ADMIN' }, isAuthenticated: true }),
}));

vi.mock('../../../api/dataopsApi', () => ({
  dataopsApi: {
    getBatchContext: vi.fn(),
    getBatchReadingResults: vi.fn(),
    startBatchReading: vi.fn(),
  },
}));

vi.mock('../context/LoteFlowContext', () => ({
  useLoteFlow: () => ({
    contexto: {
      id_lote: 35,
      estado_flujo: 'LEIDO_BETO',
      archivos: [{ id_documento: 10, nombre_archivo: 'TBL_INSCRITOS.xlsx', total_registros: 100 }],
      total_registros: 100,
    },
    readOnly: false,
    getDraft: (_k, def) => def,
    setDraft: vi.fn(),
  }),
  useDraftState: (_k, init) => [init, vi.fn()],
}));

vi.mock('../hooks/useLoteContext', () => ({
  useLoteContext: () => ({
    data: {
      id_lote: 35,
      estado_flujo: 'LEIDO_BETO',
      archivos: [{ id_documento: 10, nombre_archivo: 'TBL_INSCRITOS.xlsx', total_registros: 100 }],
      total_registros: 100,
    },
    isPending: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useLecturaBeto', () => ({
  default: () => ({
    data: {
      status: 'success',
      resumen_ejecutivo: { total_procesados: 100, aceptados_automaticamente: 90, por_revisar: 8, con_incidencias: 2 },
      pagination: { total_pages: 1, total_items: 1 },
      registros: [
        {
          id: 1,
          documento: 'TBL_INSCRITOS.xlsx',
          fila: 2,
          estudiante: 'M•••• L••••',
          ci: '••••890',
          modulo: 'DIPLOMADO EN DATOS',
          area: 'academica',
          indice_registro: 73,
          estado: 'REVISION',
          decision: { motivo_llano: 'Confianza en banda de revisión.' },
          raw_text: 'ESTUDIANTE: M•••• | PROGRAMA: DIPLOMADO EN DATOS',
          lectura: {
            entidades: [
              { label: 'ESTUDIANTE', token: 'M•••• L••••', confianza: 0.73, origen_confianza: 'BETO', lecturaModelo: 0.73 },
              { label: 'PROGRAMA', token: 'DIPLOMADO EN DATOS', confianza: 0.96, origen_confianza: 'REGLA_ENCABEZADO', detalleConfianza: { similitudEncabezado: 0.96, validez: 1.0 } },
            ],
          },
        },
      ],
    },
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));

describe('F5V V-7 y V-3 — Etiquetas del modelo, origen de confianza y claridad en lectura', () => {
  it('muestra chips de etiqueta del modelo, origen_confianza, barras AnimatedProgressBarV2, leyenda y nota de En revisión', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <NotificationProvider>
          <MemoryRouter initialEntries={['/dataops/lote/35/beto']}>
            <Routes>
              <Route path="/dataops/lote/:id/beto" element={<BetoReadingFlowView />} />
            </Routes>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(html).toContain('PER_ESTUDIANTE');
    expect(html).toContain('PROGRAMA');
    expect(html).toContain('Leído por BETO');
    expect(html).toContain('Encabezado del archivo');
    expect(html).toContain('BETO p = 0,73');
    expect(html).toContain('Regla por encabezado: similitud 0,96 · valor validado');
    expect(html).toContain('Cascada de resolución:');
    expect(html).toContain('Banda 60–85 % de lectura; el paso ③ agrupa también casos por identidad o catálogo.');
    expect(html).toContain('role="progressbar"');
  });
});
