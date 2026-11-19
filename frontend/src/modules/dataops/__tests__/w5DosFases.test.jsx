import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import fs from 'node:fs';
import path from 'node:path';

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'admin', role: 'ADMIN' } }),
}));

vi.mock('../../../api/client', () => ({
  default: {
    get: vi.fn(async () => ({ data: null })),
    post: vi.fn(async (_url, body) => ({ data: { status: 'accepted', tarea_id: 1, body } })),
  },
}));

import client from '../../../api/client';
import { dataopsApi } from '../../../api/dataopsApi';
import HumanReviewFlowView from '../HumanReviewFlowView';

describe('W-5 — Consolidación en dos fases (casos visibles antes de consolidar)', () => {
  it('dataopsApi.prepararRevision envía solo_revision=true y en_segundo_plano=true a /preparar-revision', async () => {
    const res = await dataopsApi.prepararRevision({ id_lote: 7 });
    expect(client.post).toHaveBeenCalledWith(
      '/api/v1/dataops/preparar-revision',
      expect.objectContaining({ id_lote: 7, solo_revision: true, en_segundo_plano: true })
    );
    expect(res.status).toBe('accepted');
  });

  it('HumanReviewFlowView consulta PREPARACION_REVISION y dispara prepararRevision al entrar si no corrió', () => {
    const viewPath = path.resolve(__dirname, '../HumanReviewFlowView.jsx');
    const src = fs.readFileSync(viewPath, 'utf-8');
    expect(src).toContain("'PREPARACION_REVISION'");
    expect(src).toContain('dataopsApi.prepararRevision');
    expect(src).toContain('Preparando casos de revisión');
    expect(src).toContain('prepTask === null && task === null');
    expect(src).toContain("res?.status === 'already_prepared'");
  });

  it('HumanReviewFlowView renderiza sin errores en SSR', () => {
    vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => {} });
    const qc = new QueryClient();
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/dataops/revision']}>
          <HumanReviewFlowView />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(html).toContain('Selecciona un lote desde el historial de carga.');
    vi.unstubAllGlobals();
  });
});
