import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import fs from 'node:fs';
import path from 'node:path';

const { sileoMock } = vi.hoisted(() => {
  let seq = 0;
  return {
    sileoMock: {
      show: vi.fn(() => `toast-${++seq}`),
      success: vi.fn(() => `toast-${++seq}`),
      error: vi.fn(() => `toast-${++seq}`),
      warning: vi.fn(() => `toast-${++seq}`),
      info: vi.fn(() => `toast-${++seq}`),
      action: vi.fn(() => `toast-${++seq}`),
      promise: vi.fn(),
      dismiss: vi.fn(),
      clear: vi.fn(),
    },
  };
});

vi.mock('sileo', () => ({ sileo: sileoMock }));

import { sileoToast, MAX_VISIBLE_TOASTS } from '../../../services/sileoToast';
import { notificationService } from '../../../services/notificationService';
import Button from '../../../components/shared/Button';
import GruposBandeja from '../components/GruposBandeja';

describe('W-7 — Notificaciones agrupadas y botones en carga (D-W8)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sileoToast.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('6 eventos de una misma tarea producen 1 toast activo actualizado (no 6 apilados)', () => {
    const etapas = [
      { porcentaje: 0, etapa: 'Iniciando consolidación' },
      { porcentaje: 20, etapa: 'Indexando registros' },
      { porcentaje: 40, etapa: 'Resolviendo identidades' },
      { porcentaje: 60, etapa: 'Cargando hechos académicos' },
      { porcentaje: 80, etapa: 'Cargando evaluación docente' },
      { porcentaje: 100, etapa: 'Consolidación terminada', estado: 'COMPLETADA' },
    ];

    for (let i = 0; i < etapas.length; i++) {
      notificationService.notifyTaskProgress({
        tarea_id: 99,
        title: 'Consolidación Lote #18',
        ...etapas[i],
      });
    }

    // Cada actualización previa descarta el toast anterior para mantener 1 solo toast por tarea_id
    expect(sileoMock.dismiss).toHaveBeenCalledTimes(5);
    expect(sileoToast.getActiveToastsState().visibleCount).toBe(1);
    const ultimoCall = sileoMock.success.mock.calls[0][0];
    expect(ultimoCall.description).toContain('100 %');
    expect(ultimoCall.description).toContain('Consolidación terminada');
  });

  it('5 eliminaciones en bloque se resumen en 1 toast ("5 lotes eliminados")', () => {
    vi.useFakeTimers();
    for (let i = 1; i <= 5; i++) {
      sileoToast.queueBulkDelete({ entity: 'lote', plural: 'lotes' });
    }
    expect(sileoMock.success).not.toHaveBeenCalled();
    vi.advanceTimersByTime(60);

    expect(sileoMock.success).toHaveBeenCalledTimes(1);
    expect(sileoMock.success.mock.calls[0][0].title).toBe('5 lotes eliminados');

    // También mediante notificationService.notifyBulkBatchDelete
    sileoToast.clear();
    vi.clearAllMocks();
    notificationService.notifyBulkBatchDelete([11, 12, 13, 14, 15]);
    expect(sileoMock.success).toHaveBeenCalledTimes(1);
    expect(sileoMock.success.mock.calls[0][0].title).toBe('5 lotes eliminados');
  });

  it('mantiene máximo 3 toasts visibles y agrupa el resto como "+N más"', () => {
    for (let i = 1; i <= 7; i++) {
      sileoToast.info({ title: `Aviso ${i}`, description: `Detalle ${i}` });
    }
    const state = sileoToast.getActiveToastsState();
    expect(state.visibleCount).toBe(MAX_VISIBLE_TOASTS);
    expect(state.overflowCount).toBe(4);
    const ultimaInfo = sileoMock.info.mock.calls.at(-1)[0];
    expect(ultimaInfo.title).toBe('+4 más');
  });

  it('Button muestra "Procesando…" y spinner cuando isLoading=true, y CSS respeta prefers-reduced-motion', () => {
    const html = renderToStaticMarkup(<Button isLoading>Aprobar</Button>);
    expect(html).toContain('Procesando…');
    expect(html).toContain('btn-spinner');
    expect(html).toContain('aria-busy="true"');
    expect(html).toContain('disabled=""');

    const tokensCssPath = path.resolve(process.cwd(), 'src/styles/tokens.css');
    const css = fs.readFileSync(tokensCssPath, 'utf-8');
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
    expect(css).toContain('.btn-spinner');
  });

  it('libera activeVisibleIds tras expirar el duration para no bloquear avisos futuros', () => {
    vi.useFakeTimers();
    sileoToast.info({ title: 'T1', duration: 3000 });
    sileoToast.info({ title: 'T2', duration: 3000 });
    sileoToast.info({ title: 'T3', duration: 3000 });
    expect(sileoToast.getActiveToastsState().visibleCount).toBe(3);

    vi.advanceTimersByTime(3200);
    expect(sileoToast.getActiveToastsState().visibleCount).toBe(0);

    sileoToast.info({ title: 'T4', duration: 3000 });
    const state = sileoToast.getActiveToastsState();
    expect(state.visibleCount).toBe(1);
    expect(state.overflowCount).toBe(0);
  });

  it('GruposBandeja muestra "Procesando…" con spinner cuando busy=true', () => {
    const html = renderToStaticMarkup(
      <GruposBandeja
        data={{ grupos: [{ clave: 'g1', motivo: 'HOMONIMIA', titulo: 'Homonimia', n: 5, accion_grupo: 'APROBAR' }] }}
        readOnly={false}
        busy={true}
        onVerIndividual={() => {}}
        onResolver={() => {}}
      />
    );
    expect(html).toContain('Procesando…');
    expect(html).toContain('btn-spinner');
  });
});
