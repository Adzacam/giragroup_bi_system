import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import {
  parseFormattedMetric,
  formatParsedMetric,
  easeOutQuintic,
  MOTION_DURATION_MS,
} from '../motion/useCountUpV2';
import AnimatedNumberV2 from '../motion/AnimatedNumberV2';
import AnimatedProgressBarV2 from '../motion/AnimatedProgressBarV2';
import {
  getSequentialAnimationConfig,
  withChartAnimationsV2,
  progressiveLineClipPlugin,
} from '../motion/chartAnimationsV2';
import CmiDetalleKpi from '../../modules/admin/cmi/CmiDetalleKpi';
import ProgresoTarea from '../../modules/dataops/components/ProgresoTarea';

describe('Ronda 4 (L1-R4, L2-R4, L3-R4)', () => {
  const origWindow = globalThis.window;

  beforeEach(() => {
    globalThis.document = {
      documentElement: {
        getAttribute: (attr) => (attr === 'data-ui-version' ? 'v2' : null),
      },
    };
  });

  afterEach(() => {
    globalThis.window = origWindow;
    vi.restoreAllMocks();
  });

  it('L1-R4: parseFormattedMetric y formatParsedMetric conservan prefijos, miles (.), decimales (,) y sufijos', () => {
    const casos = [
      { input: 'Bs 1.234', value: 1234, prefix: 'Bs ', suffix: '', decimals: 0 },
      { input: 'Bs. 45,2 mil', value: 45.2, prefix: 'Bs. ', suffix: ' mil', decimals: 1 },
      { input: 'Bs 1,23 M', value: 1.23, prefix: 'Bs ', suffix: ' M', decimals: 2 },
      { input: '24,5 %', value: 24.5, prefix: '', suffix: ' %', decimals: 1 },
      { input: '+2,1 pp', value: 2.1, prefix: '', suffix: ' pp', decimals: 1 },
      { input: '−15,0 %', value: -15.0, prefix: '', suffix: ' %', decimals: 1 },
      { input: '72.5%', value: 72.5, prefix: '', suffix: '%', decimals: 1 },
      { input: 42, value: 42, prefix: '', suffix: '', decimals: 0 },
    ];

    for (const c of casos) {
      const parsed = parseFormattedMetric(c.input);
      expect(parsed.isNumeric).toBe(true);
      expect(parsed.value).toBeCloseTo(c.value, 5);
      expect(parsed.prefix).toBe(c.prefix);
      expect(parsed.suffix).toBe(c.suffix);
      expect(parsed.decimals).toBe(c.decimals);
      expect(formatParsedMetric(parsed.value, parsed)).toBe(String(c.input));
    }

    for (const noNum of ['—', 'Sin dato', 'N/A', null, undefined, '']) {
      expect(parseFormattedMetric(noNum).isNumeric).toBe(false);
    }
  });

  it('L1-R4: AnimatedNumberV2 entrega el valor final exacto en SSR/reduced-motion y aplica tabular-nums', () => {
    const html = renderToStaticMarkup(<AnimatedNumberV2 value="Bs. 12.345" />);
    expect(html).toContain('Bs. 12.345');
    expect(html).toContain('tabular-nums');

    const fallbackHtml = renderToStaticMarkup(<AnimatedNumberV2 value="—" />);
    expect(fallbackHtml).toContain('—');
  });

  it('L1-R4: AnimatedProgressBarV2 respeta límites 0-100 y accesibilidad progressbar', () => {
    const html = renderToStaticMarkup(
      <AnimatedProgressBarV2 value={75} max={100} ariaLabel="Avance hacia la meta" />
    );
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="75"');
    expect(html).toContain('width:75%');

    const clamped = renderToStaticMarkup(<AnimatedProgressBarV2 value={150} max={100} />);
    expect(clamped).toContain('aria-valuenow="100"');
    expect(clamped).toContain('width:100%');
  });

  it('L2-R4: chartAnimationsV2 configura delay secuencial 45ms cuando hay movimiento y lo desactiva en reduced-motion', () => {
    // En SSR (sin window) debe desactivar animación
    expect(getSequentialAnimationConfig()).toEqual({ animation: false });

    // Con window y matchMedia(reduce: false) debe habilitar animación secuencial de 900ms
    globalThis.window = {
      matchMedia: () => ({ matches: false }),
    };

    const opts = withChartAnimationsV2({
      scales: { x: { display: true } },
      plugins: { legend: { position: 'top' } },
    });

    expect(opts.scales.x.display).toBe(true);
    expect(opts.plugins.legend.position).toBe('top');
    expect(opts.plugins.progressiveLineClip.enabled).toBe(true);
    expect(opts.animation.duration).toBe(MOTION_DURATION_MS);
    expect(opts.animation.delay({ type: 'data', mode: 'default', dataIndex: 4 })).toBe(180);
    expect(progressiveLineClipPlugin.id).toBe('progressiveLineClip');
  });

  it('L2-R4: CmiDetalleKpi renderiza pathLength=100 y puntos animados cmi-evolucion-dot', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['cmi', 'historial', 'FIN-01'], {
      codigo: 'FIN-01',
      nombre: 'Margen Operativo',
      unidad: 'PCT',
      sentido: 'MAX',
      serie: [
        { gestion: '2024', valor: 20.5, meta: 20, semaforo: 'VERDE' },
        { gestion: '2025', valor: 24.5, meta: 20, semaforo: 'VERDE' },
      ],
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiDetalleKpi codigo="FIN-01" onClose={vi.fn()} />
      </QueryClientProvider>
    );
    expect(html).toContain('pathLength="100"');
    expect(html).toContain('cmi-evolucion-path');
    expect(html).toContain('cmi-evolucion-dot');
    expect(html).toContain('animation-delay:0ms');
    expect(html).toContain('animation-delay:75ms');
  });

  it('L3-R4: ProgresoTarea integra AnimatedNumberV2 y AnimatedProgressBarV2 en modo determinado', () => {
    const html = renderToStaticMarkup(
      <ProgresoTarea
        titulo="Lectura BETO"
        tarea={{ porcentaje: 64.5, total: 100, procesados: 65, transcurrido_seg: 12 }}
      />
    );
    expect(html).toContain('64.5 %');
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="65"');
  });

  it('L2-R4: progressiveLineClipPlugin inicializa progress=0 en beforeInit y recorta el canvas progresivamente', () => {
    globalThis.window = { matchMedia: () => ({ matches: false }) };

    const ctx = {
      save: vi.fn(),
      beginPath: vi.fn(),
      rect: vi.fn(),
      clip: vi.fn(),
      restore: vi.fn(),
    };
    const chart = {
      options: { plugins: { progressiveLineClip: { enabled: true } }, animation: { duration: 900 } },
      chartArea: { left: 10, top: 20, width: 200, height: 100 },
      ctx,
    };
    const args = { meta: { type: 'line' } };

    progressiveLineClipPlugin.beforeInit(chart);
    expect(chart.$v2ClipProgress).toBe(0);

    progressiveLineClipPlugin.beforeDatasetDraw(chart, args);
    expect(ctx.save).toHaveBeenCalledTimes(1);
    expect(ctx.rect).toHaveBeenCalledWith(2, 2, 16, 136);
    expect(ctx.clip).toHaveBeenCalledTimes(1);
    expect(args.meta.$v2Clipped).toBe(true);

    progressiveLineClipPlugin.afterDatasetDraw(chart, args);
    expect(ctx.restore).toHaveBeenCalledTimes(1);
    expect(args.meta.$v2Clipped).toBe(false);

    chart.$v2ClipProgress = 1;
    progressiveLineClipPlugin.beforeDatasetDraw(chart, args);
    expect(ctx.save).toHaveBeenCalledTimes(1);
  });

  it('L1-R4: easeOutQuintic e interpolación intermedia conservan formato sin saltos', () => {
    expect(easeOutQuintic(0)).toBe(0);
    expect(easeOutQuintic(1)).toBe(1);
    expect(easeOutQuintic(0.5)).toBeGreaterThan(0.5);

    const parsedMiles = parseFormattedMetric('1.234');
    expect(parsedMiles.value).toBe(1234);
    expect(formatParsedMetric(617, parsedMiles)).toBe('617');
    expect(formatParsedMetric(1234, parsedMiles)).toBe('1.234');

    const parsedNeg = parseFormattedMetric('−15,0 %');
    expect(formatParsedMetric(0, parsedNeg)).toBe('0,0 %');
    expect(formatParsedMetric(-7.5, parsedNeg)).toBe('−7,5 %');
  });
});
