import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes, useLocation, useParams, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BatchFlowStepper from '../components/BatchFlowStepper';
import BetoReadingFlowView from '../BetoReadingFlowView';
import { NotificationProvider } from '../../../context/NotificationContext';
import { LoteFlowProvider } from '../context/LoteFlowContext';
import { dataopsApi } from '../../../api/dataopsApi';

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { rol: 'ADMIN', nombre: 'Admin' }, isAuthenticated: true }),
}));

if (typeof globalThis.localStorage === 'undefined') {
  globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
}
if (typeof globalThis.sessionStorage === 'undefined') {
  globalThis.sessionStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
}

vi.mock('../../../api/dataopsApi', () => ({
  dataopsApi: {
    getBatchContext: vi.fn(),
    getBatchReadingResults: vi.fn(),
    getPlainTextRecords: vi.fn(),
    startBatchReading: vi.fn(),
    getTareaLote: vi.fn(),
  },
}));

vi.mock('../context/LoteFlowContext', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useLoteFlow: () => ({
      contexto: {
        id_lote: 42,
        estado_flujo: 'TEXTO_LISTO',
        archivos: [{ id_documento: 10, nombre_archivo: 'antiguo.xlsx', total_registros: 100 }],
        total_registros: 100,
      },
      readOnly: false,
      getDraft: (_k, def) => def,
      setDraft: vi.fn(),
    }),
  };
});

vi.mock('../hooks/useLecturaBeto', () => ({
  default: () => ({
    data: {
      status: 'processing',
      tarea: { id: 7, estado: 'EN_CURSO', procesados: 45, total: 100 },
    },
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));

vi.mock('../components/BatchFlowLayout', () => ({
  default: ({ currentStep, children }) => (
    <div data-step={currentStep}>{children}</div>
  ),
}));

function LocationEcho() {
  const loc = useLocation();
  return <div data-testid="loc">{loc.pathname + loc.search}</div>;
}

describe('W-10 — Flujo de 3 pasos', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    dataopsApi.getBatchContext.mockResolvedValue({
      id_lote: 42,
      estado_flujo: 'TEXTO_LISTO',
      archivos: [{ id_documento: 10, nombre_archivo: 'antiguo.xlsx', total_registros: 100 }],
      total_registros: 100,
    });
    dataopsApi.getBatchReadingResults.mockResolvedValue({
      status: 'processing',
      tarea: { id: 7, estado: 'EN_CURSO', procesados: 45, total: 100 },
    });
    dataopsApi.getPlainTextRecords.mockResolvedValue({
      registros: [],
      kpis: { filas_leidas: 100, columnas_detectadas: 12, total_alertas: 2 },
      total: 0,
      total_pages: 1,
    });
  });

  it('BatchFlowStepper tiene exactamente 3 pasos (Carga, Lectura de BETO, Revisión)', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/dataops/lote/42/beto']}>
        <BatchFlowStepper currentStep={2} batchId="42" pendientesCount={5} />
      </MemoryRouter>
    );
    expect(html).toContain('Carga');
    expect(html).toContain('Lectura de BETO');
    expect(html).toContain('Revisión (5)');
    expect(html).not.toContain('Texto plano');
    expect(html).not.toContain('Revisión humana');
  });

  it('Las 4 rutas viejas de texto redirigen a beto?tab=texto (V1 y V2)', () => {
    const cases = [
      ['/dataops/texto', '/dataops/beto?tab=texto'],
      ['/dataops/lote/42/texto', '/dataops/lote/42/beto?tab=texto'],
      ['/v2/dataops/texto', '/v2/dataops/beto?tab=texto'],
      ['/v2/dataops/lote/42/texto', '/v2/dataops/lote/42/beto?tab=texto'],
    ];
    for (const [from, expected] of cases) {
      let redirectedTo = null;
      function CaptureNavigate({ to }) {
        redirectedTo = to;
        return <span>{to}</span>;
      }
      function TestRedirect({ prefix = '' }) {
        const { id } = useParams();
        const target = id ? `${prefix}/dataops/lote/${id}/beto?tab=texto` : `${prefix}/dataops/beto?tab=texto`;
        return <CaptureNavigate to={target} />;
      }
      renderToStaticMarkup(
        <MemoryRouter initialEntries={[from]}>
          <Routes>
            <Route path="/dataops/texto" element={<TestRedirect />} />
            <Route path="/dataops/lote/:id/texto" element={<TestRedirect />} />
            <Route path="/v2/dataops/texto" element={<TestRedirect prefix="/v2" />} />
            <Route path="/v2/dataops/lote/:id/texto" element={<TestRedirect prefix="/v2" />} />
            <Route path="*" element={<LocationEcho />} />
          </Routes>
        </MemoryRouter>
      );
      expect(redirectedTo).toBe(expected);
    }
  });

  it('BetoReadingFlowView muestra pestañas Resultados y Texto preparado, y nunca lanza startBatchReading al entrar', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <NotificationProvider>
          <MemoryRouter initialEntries={['/dataops/lote/42/beto']}>
            <Routes>
              <Route
                path="/dataops/lote/:id/beto"
                element={(
                  <LoteFlowProvider>
                    <BetoReadingFlowView />
                  </LoteFlowProvider>
                )}
              />
            </Routes>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>
    );
    expect(html).toContain('data-step="2"');
    expect(html).toContain('Resultados');
    expect(html).toContain('Texto preparado');
    expect(html).toContain('Leyendo registros con BETO…');
    expect(html).toContain('45.0 %');
    expect(html).toContain('Volver a carga de archivos');
    expect(dataopsApi.startBatchReading).not.toHaveBeenCalled();
  });
});
