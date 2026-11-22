import { withChartAnimationsV2 } from '../../../v2/motion/chartAnimationsV2';

function cssVar(name, fallback) {
  if (typeof window === 'undefined' || typeof document === 'undefined') return fallback;
  const target = document.querySelector('[data-ui-version]') || document.documentElement;
  const val = getComputedStyle(target).getPropertyValue(name).trim();
  return val || fallback;
}

export function getChartTokens(isDark) {
  return {
    text: cssVar('--color-ink-black', isDark ? 'rgb(250, 249, 246)' : 'rgb(23, 25, 28)'),
    muted: cssVar('--color-slate-gray', isDark ? 'rgb(156, 163, 175)' : 'rgb(119, 123, 134)'),
    navy: cssVar('--color-gira-navy', isDark ? 'rgb(250, 249, 246)' : 'rgb(12, 30, 51)'),
    gold: cssVar('--color-gira-gold', isDark ? 'rgb(241, 184, 68)' : 'rgb(217, 155, 38)'),
    goldLight: cssVar('--color-gira-gold-light', isDark ? 'rgb(246, 200, 102)' : 'rgb(241, 184, 68)'),
    ok: cssVar('--color-alert-green', 'rgb(27, 135, 84)'),
    warn: cssVar('--color-alert-amber', 'rgb(180, 83, 9)'),
    bad: cssVar('--color-alert-red', 'rgb(217, 56, 58)'),
    grid: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
    tooltipBg: isDark ? 'rgb(32, 37, 46)' : 'rgb(12, 30, 51)',
    tooltipText: cssVar('--color-alabaster', 'rgb(250, 249, 246)'),
    icBand: 'rgba(217, 155, 38, 0.14)',
    metaBarBg: isDark ? 'rgba(119, 123, 134, 0.35)' : 'rgba(12, 30, 51, 0.18)',
  };
}

export function buildChartOptions(isDark, extra = {}) {
  const t = getChartTokens(isDark);
  return withChartAnimationsV2({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: t.muted, font: { family: 'var(--font-sohne)', size: 11 } },
      },
      tooltip: {
        backgroundColor: t.tooltipBg,
        titleColor: t.tooltipText,
        bodyColor: t.tooltipText,
        padding: 10,
        borderRadius: 8,
      },
      ...(extra.plugins || {}),
    },
    scales: {
      x: { grid: { color: t.grid }, ticks: { color: t.muted, font: { family: 'var(--font-sohne)', size: 10 } } },
      y: { grid: { color: t.grid }, ticks: { color: t.muted, font: { family: 'var(--font-sohne)', size: 10 } } },
      ...(extra.scales || {}),
    },
    ...extra,
  });
}
