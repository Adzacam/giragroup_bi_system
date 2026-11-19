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
    getLoteContext: vi.fn(async () => ({
      id_lote: 18,
      estado_flujo: 'LEIDO_BETO',
      total_registros: 100,
      pendientes_revision: 0,
      archivos: [{ id_documento: 28, nombre_archivo: 'eval.xlsx', total_registros: 100 }],
    })),
    getBatchReading: vi.fn(async () => ({ status: 'not_started' })),
    getPreparedText: vi.fn(async () => ({
      registros: [],
      kpis: { filas_leidas: 100, columnas_detectadas: 12, total_alertas: 3 },
      total: 0,
      total_pages: 1,
    })),
  },
}));

import { toDataopsPath } from '../../../v2/utils/v2Routes';
import betoMetricas from '../../../constants/betoMetricas.json';
import BetoMetricasModal from '../components/BetoMetricasModal';
import BetoReadingFlowView from '../BetoReadingFlowView';
import PlainTextTransformationView from '../PlainTextTransformationView';

const REPO_ROOT = path.resolve(__dirname, '../../../../..');
const FRONT_SRC = path.join(REPO_ROOT, 'frontend', 'src');

function walkFiles(dir, exts = ['.js', '.jsx', '.ts', '.tsx']) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkFiles(full, exts));
    } else if (exts.some((ext) => entry.name.endsWith(ext))) {
      out.push(full);
    }
  }
  return out;
}

describe('W-9 — Rutas DataOps, KPIs animados y Métricas del modelo BETO', () => {
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

  it('toDataopsPath preserva el prefijo /v2 cuando la ruta actual está en /v2/*', () => {
    expect(toDataopsPath('/ingesta', '/v2/dataops/lote/18/beto')).toBe('/v2/dataops/ingesta');
    expect(toDataopsPath('/lote/18/revision', '/v2/dataops/lote/18/beto')).toBe('/v2/dataops/lote/18/revision');
    expect(toDataopsPath('/dataops/lote/18/texto', '/v2/dataops/ingesta')).toBe('/v2/dataops/lote/18/texto');
    expect(toDataopsPath('ingesta', '/v2')).toBe('/v2/dataops/ingesta');

    expect(toDataopsPath('/ingesta', '/dataops/lote/18/beto')).toBe('/dataops/ingesta');
    expect(toDataopsPath('/lote/18/revision', '/dataops/lote/18/beto')).toBe('/dataops/lote/18/revision');
    expect(toDataopsPath('/dataops/ingesta', '/dataops/lote/18/texto')).toBe('/dataops/ingesta');
  });

  it('mantiene 0 llamadas fijas navigate("/dataops/...") en frontend/src (excluyendo HumanReviewFlowView.jsx en paralelo)', () => {
    const files = walkFiles(FRONT_SRC).filter(
      (f) => !f.endsWith('HumanReviewFlowView.jsx') && !f.includes(`${path.sep}__tests__${path.sep}`)
    );
    const regex = /navigate\s*\([^)]*(['"`])\/dataops\//;
    const matches = [];
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (regex.test(content)) {
        matches.push(path.relative(REPO_ROOT, file));
      }
    }
    expect(matches).toEqual([]);
  });

  it('no contiene textos visibles con "Tarea 1..." o "Tarea 2..." en frontend/src', () => {
    const files = walkFiles(FRONT_SRC).filter((f) => !f.includes(`${path.sep}__tests__${path.sep}`));
    const regex = /tarea\s+[12]\d*/i;
    const matches = [];
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (regex.test(content)) {
        matches.push(path.relative(REPO_ROOT, file));
      }
    }
    expect(matches).toEqual([]);
  });

  it('cada cifra de betoMetricas.json y del modal coincide exactamente con los JSON de docs/mediciones/', () => {
    const f3rMatriz = JSON.parse(
      fs.readFileSync(path.join(REPO_ROOT, 'docs/mediciones/f3r_matriz_confusion.json'), 'utf-8')
    );
    const f3rAblacion = JSON.parse(
      fs.readFileSync(path.join(REPO_ROOT, 'docs/mediciones/f3r_ablacion.json'), 'utf-8')
    );
    const f1Training = JSON.parse(
      fs.readFileSync(path.join(REPO_ROOT, 'docs/mediciones/f1_training_info.json'), 'utf-8')
    );
    const matriz5x5Src = JSON.parse(
      fs.readFileSync(path.join(REPO_ROOT, 'docs/mediciones/f1_evaluacion_despues/matriz_confusion_ner.json'), 'utf-8')
    );

    const modoCStrict = f3rAblacion.filas.find(
      (r) => r.dataset === 'gold_510' && r.modo === 'C' && r.criterio === 'strict'
    );
    const modoCRelaxed = f3rAblacion.filas.find(
      (r) => r.dataset === 'gold_510' && r.modo === 'C' && r.criterio === 'relaxed'
    );

    expect(betoMetricas.ficha_modelo.model_base).toBe(f1Training.model_base);
    expect(betoMetricas.ficha_modelo.num_etiquetas).toBe(f1Training.classes.length);
    expect(betoMetricas.ficha_modelo.etiquetas_iob2).toEqual(f1Training.classes);
    expect(betoMetricas.ficha_modelo.best_dev_f1).toBe(f1Training.best_dev_f1);
    expect(betoMetricas.ficha_modelo.best_epoch).toBe(f1Training.best_epoch);
    expect(betoMetricas.epocas).toHaveLength(f1Training.epoch_history.length);
    expect(betoMetricas.gold_510_modo_c.estricto.f1).toBe(Number(modoCStrict.f1));
    expect(betoMetricas.gold_510_modo_c.relajado.f1).toBe(Number(modoCRelaxed.f1));
    expect(betoMetricas.matriz_confusion_5x5.matriz).toEqual(matriz5x5Src.matriz);

    const html = renderToStaticMarkup(<BetoMetricasModal isOpen onClose={() => {}} />);

    const fmtPct = (v) =>
      `${(v * 100).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %`;
    const fmt4 = (v) =>
      v.toLocaleString('es-BO', { minimumFractionDigits: 4, maximumFractionDigits: 4 });

    expect(html).toContain(f1Training.model_base);
    expect(html).toContain(`${f1Training.classes.length} etiquetas IOB2`);
    expect(html).toContain(fmtPct(Number(modoCStrict.f1)));
    expect(html).toContain(fmtPct(Number(modoCRelaxed.f1)));
    expect(html).toContain(fmt4(f1Training.best_dev_f1));

    for (const [clase, stats] of Object.entries(f3rMatriz.por_tipo_estricto)) {
      expect(html).toContain(clase);
      expect(html).toContain(fmtPct(stats.f1));
      expect(html).toContain(fmtPct(f3rMatriz.f1_relajado_por_tipo[clase]));
    }

    for (const ep of f1Training.epoch_history) {
      expect(html).toContain(`Época ${ep.epoch}`);
      expect(html).toContain(fmt4(ep.dev_f1));
    }

    const idxEst = matriz5x5Src.clases.indexOf('PER_ESTUDIANTE');
    const idxProg = matriz5x5Src.clases.indexOf('PROGRAMA');
    const confToken = matriz5x5Src.matriz[idxEst][idxProg];
    expect(confToken).toBe(1);
    expect(html).toContain(`${confToken} token PER_ESTUDIANTE → PROGRAMA`);
  });

  it('BetoReadingFlowView renderiza el botón "Métricas del modelo" y PlainTextTransformationView usa AnimatedNumberV2', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const betoHtml = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/v2/dataops/lote/18/beto']}>
          <BetoReadingFlowView />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(betoHtml).toContain('Métricas del modelo');

    const plainSrc = fs.readFileSync(
      path.join(FRONT_SRC, 'modules/dataops/PlainTextTransformationView.jsx'),
      'utf-8'
    );
    expect(plainSrc).toContain('AnimatedNumberV2');
    expect(plainSrc).toContain('toDataopsPath');
  });
});
