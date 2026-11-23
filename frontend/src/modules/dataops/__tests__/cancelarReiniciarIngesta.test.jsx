import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import fs from 'node:fs';
import path from 'node:path';

vi.mock('sileo', () => ({
  sileo: {
    show: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    action: vi.fn(),
    promise: vi.fn(),
    dismiss: vi.fn(),
    clear: vi.fn(),
  },
}));

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { rol: 'ADMIN', nombre: 'Admin' }, isAuthenticated: true }),
}));

vi.mock('../../../api/dataopsApi', () => ({
  dataopsApi: {
    getBatchHistory: vi.fn(async () => ({ total: 0, data: [] })),
    reiniciarLote: vi.fn(async () => ({ status: 'success' })),
    cancelarTarea: vi.fn(async () => ({ status: 'success', cancelada: true })),
  },
}));

import ProgresoTarea from '../components/ProgresoTarea';
import IngestDropzonePanel from '../components/IngestDropzonePanel';
import IngestRulesPanel from '../components/IngestRulesPanel';
import BatchHistory from '../components/BatchHistory';

describe('DataOps — Botones de Cancelar y Reiniciar ingesta', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('ProgresoTarea renderiza botón Cancelar cuando recibe onCancel', () => {
    const htmlCon = renderToStaticMarkup(
      <ProgresoTarea
        titulo="Leyendo… 40 %"
        tarea={{ id: 7, total: 100, procesados: 40, porcentaje: 40, transcurrido_seg: 12 }}
        onCancel={() => {}}
        cancelLabel="Cancelar lectura"
      />
    );
    expect(htmlCon).toContain('Cancelar lectura');
    expect(htmlCon).toContain('dataops-btn-danger');

    const htmlSin = renderToStaticMarkup(
      <ProgresoTarea
        titulo="Leyendo… 40 %"
        tarea={{ id: 7, total: 100, procesados: 40, porcentaje: 40, transcurrido_seg: 12 }}
      />
    );
    expect(htmlSin).not.toContain('Cancelar lectura');
  });

  it('IngestDropzonePanel e IngestRulesPanel muestran Cancelar carga solo mientras isProcessing=true', () => {
    const htmlDropzoneActivo = renderToStaticMarkup(
      <IngestDropzonePanel
        dropzoneRef={{ current: null }}
        isDragging={false}
        setIsDragging={() => {}}
        isProcessing={true}
        isCheckingFiles={false}
        uploadProgress={45}
        isFormValid={true}
        queuedFiles={[{ uid: '1', file: { name: 'a.xlsx', size: 100 } }]}
        selectedQueueFiles={[{ uid: '1' }]}
        onDrop={() => {}}
        onFileSelect={() => {}}
        onProcessBatch={() => {}}
        onClearQueue={() => {}}
        onCancelUpload={() => {}}
      />
    );
    expect(htmlDropzoneActivo).toContain('Cancelar carga');

    const htmlDropzoneInactivo = renderToStaticMarkup(
      <IngestDropzonePanel
        dropzoneRef={{ current: null }}
        isDragging={false}
        setIsDragging={() => {}}
        isProcessing={false}
        isCheckingFiles={false}
        uploadProgress={0}
        isFormValid={false}
        queuedFiles={[]}
        selectedQueueFiles={[]}
        onDrop={() => {}}
        onFileSelect={() => {}}
        onProcessBatch={() => {}}
        onClearQueue={() => {}}
        onCancelUpload={() => {}}
      />
    );
    expect(htmlDropzoneInactivo).not.toContain('Cancelar carga');

    const htmlRulesActivo = renderToStaticMarkup(
      <IngestRulesPanel
        isProcessing={true}
        uploadProgress={60}
        uploadStageText="Subiendo..."
        onCancelUpload={() => {}}
      />
    );
    expect(htmlRulesActivo).toContain('Cancelar');
  });

  it('BatchHistory muestra Reiniciar para lotes no consolidados con archivos y lo omite en CONSOLIDADO o ERROR sin archivos', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['dataops', 'historial', 1], {
      total: 3,
      data: [
        { id_lote: 20, id_documento: 200, name: 'equivo.xlsx', status: 'TEXTO_LISTO', total_archivos: 1, puede_eliminar: false },
        { id_lote: 21, id_documento: 201, name: 'ok.xlsx', status: 'CONSOLIDADO', total_archivos: 1, puede_eliminar: false },
        { id_lote: 22, id_documento: null, name: 'Lote #22', status: 'ERROR', total_archivos: 0, puede_eliminar: true },
      ],
    });

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/dataops/ingesta']}>
        <QueryClientProvider client={qc}>
          <BatchHistory
            onInspect={() => {}}
            onLogs={() => {}}
            onNewBatch={() => {}}
            loadingLogs={null}
            inspecting={false}
            disabled={false}
          />
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(html).toContain('Reiniciar');
    expect(html).toContain('Eliminar');
    // Solo una fila (id_lote=20) debe renderizar el botón Reiniciar
    expect(html.match(/>Reiniciar</g)?.length).toBe(1);
  });

  it('dataops-flow.css define tokens de peligro para modo claro y [data-theme="dark"]', () => {
    const cssPath = path.resolve(process.cwd(), 'src/styles/dataops-flow.css');
    const css = fs.readFileSync(cssPath, 'utf-8');
    expect(css).toContain('--dataops-danger-bg');
    expect(css).toContain('--dataops-danger-border');
    expect(css).toContain('--dataops-danger-text');
    expect(css).toContain('.dataops-btn-danger');
  });

  it('HumanReviewFlowView define refetchTask en el query de consolidacion-task para evitar ReferenceError al cancelar', () => {
    const viewPath = path.resolve(process.cwd(), 'src/modules/dataops/HumanReviewFlowView.jsx');
    const src = fs.readFileSync(viewPath, 'utf-8');
    expect(src).toMatch(/refetch:\s*refetchTask/);
    expect(src).toContain('refetchTask()');
  });
});
