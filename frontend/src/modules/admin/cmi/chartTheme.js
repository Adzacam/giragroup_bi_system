import { withChartAnimationsV2 } from '../../../v2/motion/chartAnimationsV2';

function cssVar(name, fallback) {
  if (typeof window === 'undefined' || typeof document === 'undefined') return fallback;
  const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return val || fallback;
}

export function getChartTokens(isDark) {
  return {
    text: cssVar('--color-ink-black', isDark ? '#FAF9F6' : '#17191C'),
    muted: cssVar('--color-slate-gray', isDark ? '#9CA3AF' : '#777B86'),
    navy: cssVar('--color-gira-navy', isDark ? '#FAF9F6' : '#0C1E33'),
    gold: cssVar('--color-gira-gold', '#D99B26'),
    goldLight: cssVar('--color-gira-gold-light', '#F1B844'),
    ok: cssVar('--color-alert-green', '#1B8754'),
    warn: cssVar('--color-alert-amber', '#B45309'),
    bad: cssVar('--color-alert-red', '#D9383A'),
    grid: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
    tooltipBg: isDark ? '#20252E' : '#0C1E33',
    tooltipText: '#FAF9F6',
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
