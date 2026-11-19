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
    getLoteContext: vi.fn(async () => null),
    getBatchHistory: vi.fn(async () => ({
      total: 2,
      data: [
        { id_lote: 10, name: 'Lote #10', status: 'ERROR', total_archivos: 1, puede_eliminar: true, puede_reintentar_lectura: true },
        { id_lote: 11, name: 'Lote #11', status: 'CONSOLIDADO', total_archivos: 2, puede_eliminar: false, puede_reintentar_lectura: false },
      ],
    })),
    deleteFailedBatch: vi.fn(async () => ({ ok: true })),
    retryBatchReading: vi.fn(async () => ({ ok: true })),
  },
}));

import {
  getAccionesBloqueHabilitadas,
  getSelectedQueueFiles,
  isAllBatchesSelected,
  isAllQueueSelected,
  puedeEliminarLote,
  puedeReintentarLote,
  toggleBatchSelection,
  toggleSelectAllBatches,
  toggleSelectAllQueue,
  toggleUidSelection,
  validateQueueSelection,
} from '../utils/cargaHistorialHelpers';
import IngestView from '../IngestView';
import BatchHistory from '../components/BatchHistory';

describe('W-8 — Rediseño de la carga y del historial', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const store = {};
    globalThis.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
      clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    };
  });

  describe('Cola de archivos: selección y validación', () => {
    const queue = [
      { uid: 'u1', file: { name: 'arca.xlsx', size: 1024 }, sourceType: 'ACTA', tipoEscala: '0-100', status: 'En cola' },
      { uid: 'u2', file: { name: 'eval.xlsx', size: 2048 }, sourceType: 'EVALUACION_DOCENTE', tipoEscala: null, status: 'En cola' },
      { uid: 'u3', file: { name: 'desconocido.xlsx', size: 512 }, sourceType: '', tipoEscala: null, status: 'En cola' },
    ];

    it('permite seleccionar/deseleccionar individualmente y con "Seleccionar todo"', () => {
      let selected = toggleSelectAllQueue(queue, []);
      expect(selected).toEqual(['u1', 'u2', 'u3']);
      expect(isAllQueueSelected(queue, selected)).toBe(true);

      selected = toggleUidSelection(selected, 'u3');
      expect(selected).toEqual(['u1', 'u2']);
      expect(isAllQueueSelected(queue, selected)).toBe(false);

      // Si no están todos seleccionados, "Seleccionar todo" selecciona los faltantes
      selected = toggleSelectAllQueue(queue, selected);
      expect(selected).toEqual(['u1', 'u2', 'u3']);
      expect(isAllQueueSelected(queue, selected)).toBe(true);

      // Si ya están todos seleccionados, "Seleccionar todo" vacía la selección
      selected = toggleSelectAllQueue(queue, selected);
      expect(selected).toEqual([]);
      expect(isAllQueueSelected(queue, selected)).toBe(false);
    });

    it('valida solo los archivos seleccionados (ACTA/MOODLE requieren escala, EVALUACION_DOCENTE no)', () => {
      const soloValidos = getSelectedQueueFiles(queue, ['u1', 'u2']);
      expect(validateQueueSelection(soloValidos)).toEqual({
        valid: true,
        selectedCount: 2,
        missingSourceTypeCount: 0,
        missingScaleCount: 0,
      });

      // Si se selecciona el archivo sin tipo, falla
      const conSinTipo = getSelectedQueueFiles(queue, ['u1', 'u3']);
      expect(validateQueueSelection(conSinTipo).valid).toBe(false);
      expect(validateQueueSelection(conSinTipo).missingSourceTypeCount).toBe(1);

      // ACTA sin escala falla
      const actaSinEscala = [{ uid: 'u4', sourceType: 'ACTA', tipoEscala: '' }];
      expect(validateQueueSelection(actaSinEscala).valid).toBe(false);
      expect(validateQueueSelection(actaSinEscala).missingScaleCount).toBe(1);

      // MOODLE sin escala falla, con escala pasa
      const moodleSinEscala = [{ uid: 'u5', sourceType: 'MOODLE', tipoEscala: '' }];
      expect(validateQueueSelection(moodleSinEscala).valid).toBe(false);
      expect(validateQueueSelection([{ uid: 'u5', sourceType: 'MOODLE', tipoEscala: '0-10' }]).valid).toBe(true);

      // Exceder maxFiles o falta de institución falla
      expect(validateQueueSelection(soloValidos, 1).valid).toBe(false);
      expect(validateQueueSelection(soloValidos, 10, '').valid).toBe(false);

      // Selección vacía falla
      expect(validateQueueSelection([]).valid).toBe(false);
      expect(isAllQueueSelected([], [])).toBe(false);
      expect(toggleSelectAllQueue([], [])).toEqual([]);
    });
  });

  describe('Historial de lotes: selección y acciones en bloque por estado', () => {
    const loteErrorAmbos = { id_lote: 1, status: 'ERROR', puede_eliminar: true, puede_reintentar_lectura: true };
    const loteErrorSoloEliminar = { id_lote: 2, status: 'ERROR', puede_eliminar: true, puede_reintentar_lectura: false };
    const loteErrorSoloReintentar = { id_lote: 3, status: 'ERROR', puede_eliminar: false, puede_reintentar_lectura: true };
    const loteConsolidado = { id_lote: 4, status: 'CONSOLIDADO', puede_eliminar: false, puede_reintentar_lectura: false };
    const loteEnRevision = { id_lote: 5, status: 'EN_REVISION', puede_eliminar: false, puede_reintentar_lectura: false };

    it('evalúa correctamente los permisos individuales por estado', () => {
      expect(puedeEliminarLote(loteErrorAmbos)).toBe(true);
      expect(puedeReintentarLote(loteErrorAmbos)).toBe(true);
      expect(puedeEliminarLote(loteConsolidado)).toBe(false);
      expect(puedeReintentarLote(loteConsolidado)).toBe(false);
      expect(puedeEliminarLote(loteEnRevision)).toBe(false);
      expect(puedeEliminarLote({ id_lote: 6, status: 'CONSOLIDADO', puede_eliminar: true })).toBe(false);
      expect(puedeReintentarLote({ id_lote: 7, status: 'CARGADO', puede_reintentar_lectura: true })).toBe(false);
      expect(puedeEliminarLote(null)).toBe(false);
    });

    it('habilita acciones en bloque SOLO si todos los lotes seleccionados lo permiten', () => {
      expect(getAccionesBloqueHabilitadas([])).toEqual({ count: 0, canDelete: false, canRetry: false });

      // Todos ERROR con ambos permisos -> ambos habilitados
      expect(getAccionesBloqueHabilitadas([loteErrorAmbos])).toEqual({
        count: 1,
        canDelete: true,
        canRetry: true,
      });

      // ERROR (ambos) + ERROR (solo eliminar) -> solo eliminar
      expect(getAccionesBloqueHabilitadas([loteErrorAmbos, loteErrorSoloEliminar])).toEqual({
        count: 2,
        canDelete: true,
        canRetry: false,
      });

      // ERROR (ambos) + ERROR (solo reintentar) -> solo reintentar
      expect(getAccionesBloqueHabilitadas([loteErrorAmbos, loteErrorSoloReintentar])).toEqual({
        count: 2,
        canDelete: false,
        canRetry: true,
      });

      // Mezcla con CONSOLIDADO o EN_REVISION -> ninguna acción en bloque
      expect(getAccionesBloqueHabilitadas([loteErrorAmbos, loteConsolidado])).toEqual({
        count: 2,
        canDelete: false,
        canRetry: false,
      });
      expect(getAccionesBloqueHabilitadas([loteErrorAmbos, loteEnRevision])).toEqual({
        count: 2,
        canDelete: false,
        canRetry: false,
      });
    });

    it('gestiona seleccionar todo e individual en el historial', () => {
      const rows = [loteErrorAmbos, loteConsolidado];
      let sel = toggleSelectAllBatches(rows, []);
      expect(sel).toEqual([1, 4]);
      expect(isAllBatchesSelected(rows, sel)).toBe(true);

      sel = toggleBatchSelection(sel, 4);
      expect(sel).toEqual([1]);
      expect(isAllBatchesSelected(rows, sel)).toBe(false);
    });
  });

  describe('Renderizado de IngestView, BatchHistory y CSS responsive', () => {
    const createClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

    it('IngestView renderiza "Procesar seleccionados" y "Vaciar cola" junto a la zona de carga y omite el panel "Archivo seleccionado"', () => {
      const html = renderToStaticMarkup(
        <MemoryRouter initialEntries={['/dataops/ingesta']}>
          <QueryClientProvider client={createClient()}>
            <IngestView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(html).toContain('Procesar seleccionados');
      expect(html).toContain('Vaciar cola');
      expect(html).not.toContain('Archivo seleccionado');
    });

    it('BatchHistory renderiza casilla "Seleccionar todo" y casillas por lote cuando hay datos en caché', () => {
      const qc = createClient();
      qc.setQueryData(['dataops', 'historial', 1], {
        total: 2,
        data: [
          { id_lote: 10, name: 'Lote #10', status: 'ERROR', total_archivos: 1, puede_eliminar: true, puede_reintentar_lectura: true },
          { id_lote: 11, name: 'Lote #11', status: 'CONSOLIDADO', total_archivos: 2, puede_eliminar: false, puede_reintentar_lectura: false },
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

      expect(html).toContain('aria-label="Seleccionar todo"');
      expect(html).toContain('aria-label="Seleccionar lote #10"');
      expect(html).toContain('aria-label="Seleccionar lote #11"');
      expect(html).not.toContain('Eliminar seleccionados');
      expect(html).not.toContain('Reintentar seleccionados');
    });

    it('dataops-flow.css incluye regla responsive <= 960px para .dataops-section-a y white-space: normal en .dataops-row-detail (sin scroll horizontal a 375px)', () => {
      const cssPath = path.resolve(process.cwd(), 'src/styles/dataops-flow.css');
      const css = fs.readFileSync(cssPath, 'utf-8');
      expect(css).toContain('.dataops-section-a > *');
      expect(css).toContain('grid-template-columns: 1fr');
      expect(css).toContain('.dataops-queue-actions');
      expect(css).toContain('.dataops-bulk-bar');
      expect(css).toContain('.dataops-row-detail');
      expect(css).toContain('white-space: normal');
    });
  });
});
