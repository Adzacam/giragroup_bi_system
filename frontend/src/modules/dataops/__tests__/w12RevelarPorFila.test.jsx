import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../../api/dataopsApi', () => ({
  dataopsApi: {
    getPlainTextRecords: vi.fn(),
    revelarCampo: vi.fn(),
    revelarCi: vi.fn(),
  },
}));

vi.mock('../hooks/useTextoPreparado', () => ({
  default: () => ({
    data: {
      registros: [
        {
          stg_id: 10,
          line_number: 1,
          nombre_archivo: 'eval.xlsx',
          fila_original: ['NOMBRE: ••••', 'CORREO: ••••@••••'],
          oracion_beto: 'NOMBRE: •••• | CORREO: ••••@••••',
        },
      ],
      total: 1,
      total_pages: 1,
      diagnosticos: [],
    },
    error: null,
    isFetching: false,
    isPending: false,
    refetch: vi.fn(),
  }),
}));

import TextoPreparadoTab from '../components/TextoPreparadoTab';
import { CasoRevision } from '../HumanReviewFlowView';

describe('W-12 — Revelar nombre y correo por fila', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('TextoPreparadoTab renderiza botones Revelar nombre y Revelar correo por fila', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <TextoPreparadoTab batchId="42" selectedDocId={null} context={{ id_lote: 42, archivos: [] }} />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(html).toContain('Revelar nombre');
    expect(html).toContain('Revelar correo');
  });

  it('CasoRevision renderiza botones Revelar nombre, Revelar correo y Revelar con auditoría sin exponer nombre', () => {
    const html = renderToStaticMarkup(
      <CasoRevision
        item={{
          id: 55,
          motivo: 'HOMONIMIA',
          estudiante: '••••',
          ci_enmascarado: '••••019',
          tiene_correo: true,
          correo_enmascarado: '••••@••••',
          campos_correccion: [{ name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true }],
        }}
        readOnly={false}
        busy={false}
        schedule={vi.fn()}
      />
    );
    expect(html).toContain('Revelar nombre');
    expect(html).toContain('Revelar correo');
    expect(html).toContain('Revelar con auditoría');
    expect(html).toContain('••••@••••');
  });

  it('CasoRevision oculta Revelar correo cuando la fila no tiene correo', () => {
    const html = renderToStaticMarkup(
      <CasoRevision
        item={{
          id: 56,
          motivo: 'HOMONIMIA',
          estudiante: '••••',
          ci_enmascarado: '••••019',
          tiene_correo: false,
          correo_enmascarado: null,
          campos_correccion: [{ name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true }],
        }}
        readOnly={false}
        busy={false}
        schedule={vi.fn()}
      />
    );
    expect(html).toContain('Revelar nombre');
    expect(html).not.toContain('Revelar correo');
  });

  it('CasoRevision oculta Revelar correo cuando correo_enmascarado es No provisto', () => {
    const html = renderToStaticMarkup(
      <CasoRevision
        item={{
          id: 57,
          motivo: 'HOMONIMIA',
          estudiante: '••••',
          ci_enmascarado: '••••019',
          tiene_correo: false,
          correo_enmascarado: 'No provisto',
          campos_correccion: [{ name: 'nombre_completo', label: 'Nombre completo', type: 'text', required: true }],
        }}
        readOnly={false}
        busy={false}
        schedule={vi.fn()}
      />
    );
    expect(html).not.toContain('Revelar correo');
  });
});
