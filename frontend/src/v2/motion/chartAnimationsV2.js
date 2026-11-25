import { MOTION_DURATION_MS, prefersReducedMotion } from './useCountUpV2';

/**
 * Plugin Chart.js que recorta progresivamente de izquierda a derecha
 * las series de línea durante la animación inicial para lograr un trazado punto a punto.
 */
export const progressiveLineClipPlugin = {
  id: 'progressiveLineClip',
  beforeInit(chart) {
    const enabled = chart.options?.plugins?.progressiveLineClip?.enabled;
    if (chart.$v2InitialAnimDone) {
      chart.$v2ClipProgress = 1;
    } else if (enabled && chart.options?.animation !== false && !prefersReducedMotion()) {
      chart.$v2ClipProgress = 0;
    }
  },
  beforeDatasetDraw(chart, args) {
    const enabled = chart.options?.plugins?.progressiveLineClip?.enabled;
    if (!enabled || prefersReducedMotion()) return;
    if (args?.meta?.type !== 'line') return;

    const progress = chart.$v2ClipProgress;
    if (typeof progress !== 'number' || progress >= 1) return;
    if (!chart.chartArea) return;

    const { left, top, width, height } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.rect(left - 8, top - 18, Math.max(0, width * progress + 16), height + 36);
    ctx.clip();
    args.meta.$v2Clipped = true;
  },
  afterDatasetDraw(chart, args) {
    if (args?.meta?.$v2Clipped) {
      chart.ctx.restore();
      args.meta.$v2Clipped = false;
    }
  },
};

export const CHART_PLUGINS_V2 = [progressiveLineClipPlugin];

/**
 * Genera configuración de animación secuencial punto a punto (45ms por índice)
 * y crecimiento vertical suave en 900ms, respetando `prefers-reduced-motion`.
 */
export function getSequentialAnimationConfig({ duration = MOTION_DURATION_MS, stepDelayMs = 45 } = {}) {
  if (prefersReducedMotion()) {
    return { animation: false };
  }

  return {
    animation: {
      duration,
      easing: 'easeOutQuart',
      delay(ctx) {
        if (ctx.type === 'data' && ctx.mode === 'default') {
          return Math.min(ctx.dataIndex * stepDelayMs, 650);
        }
        return 0;
      },
      onProgress(anim) {
        if (anim?.chart && !anim.chart.$v2InitialAnimDone && anim.numSteps > 0) {
          anim.chart.$v2ClipProgress = Math.min(1, anim.currentStep / anim.numSteps);
        }
      },
      onComplete(anim) {
        if (anim?.chart) {
          anim.chart.$v2InitialAnimDone = true;
          anim.chart.$v2ClipProgress = 1;
        }
      },
    },
    transitions: {
      active: { animation: { duration: 0 } },
    },
    animations: {
      y: {
        from(ctx) {
          if (ctx.type === 'data' && ctx.mode === 'default' && !ctx.chart?.$v2InitialAnimDone && ctx.chart?.scales?.y) {
            return ctx.chart.scales.y.getPixelForValue(0);
          }
          return undefined;
        },
      },
    },
  };
}

/**
 * Combina las opciones existentes de Chart.js con las animaciones V2
 * sin alterar tooltips, leyendas ni escalas.
 */
export function withChartAnimationsV2(baseOptions = {}, { clipLines = true, duration = MOTION_DURATION_MS } = {}) {
  const seq = getSequentialAnimationConfig({ duration });
  return {
    ...baseOptions,
    ...seq,
    plugins: {
      ...(baseOptions.plugins || {}),
      progressiveLineClip: {
        enabled: clipLines && !prefersReducedMotion(),
      },
    },
  };
}
