import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { getChartTokens, buildChartOptions } from '../chartTheme';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export const fmtBs = (v) =>
  v === null || v === undefined || Number.isNaN(Number(v))
    ? '—'
    : Math.round(Number(v)).toLocaleString('es-BO');

export function buildCaso1Data(macroData, isDark) {
  const c1 = macroData?.caso1_demanda_global;
  if (!c1) return null;
  const t = getChartTokens(isDark);
  const labels = [...c1.periodos_historicos, ...c1.periodos_proyectados];
  const historicalSeries = [...c1.valores_historicos, ...Array(c1.periodos_proyectados.length).fill(null)];
  const lastHistVal = c1.valores_historicos[c1.valores_historicos.length - 1];
  const hwSeries = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.forecast_hw];
  const icUpper = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.ic_upper_95];
  const icLower = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.ic_lower_95];

  return {
    labels,
    datasets: [
      {
        label: 'Inscritos Históricos',
        data: historicalSeries,
        borderColor: t.navy,
        backgroundColor: t.navy,
        borderWidth: 2.2,
        pointRadius: 2.5,
        tension: 0.2,
      },
      {
        label: 'Proyección Holt-Winters Amortiguado (m=12)',
        data: hwSeries,
        borderColor: t.gold,
        backgroundColor: t.gold,
        borderWidth: 2.6,
        borderDash: [6, 4],
        pointRadius: 4,
        tension: 0.2,
      },
      {
        label: 'Banda IC 95% Superior',
        data: icUpper,
        borderColor: 'transparent',
        backgroundColor: t.icBand,
        pointRadius: 0,
        fill: '+1',
      },
      {
        label: 'Banda IC 95% Inferior (ŷ ≥ 0)',
        data: icLower,
        borderColor: 'transparent',
        backgroundColor: t.icBand,
        pointRadius: 0,
        fill: false,
      },
      {
        label: 'Tendencia OLS Indicativa',
        data: c1.recta_ols_full || [],
        borderColor: t.ok,
        borderWidth: 1.6,
        pointRadius: 0,
        borderDash: [2, 3],
        fill: false,
      },
    ],
  };
}

export function buildCaso3Data(macroData, isDark) {
  const c3 = macroData?.caso3_metas_mensuales;
  if (!c3) return null;
  const t = getChartTokens(isDark);
  return {
    labels: c3.meses_etiquetas || [],
    datasets: [
      {
        type: 'bar',
        label: 'Meta Presupuestaria de Catálogo (Bs)',
        data: c3.meta_catalogo_bs,
        backgroundColor: t.metaBarBg,
        borderColor: t.navy,
        borderWidth: 1,
        borderRadius: 6,
      },
      {
        type: 'line',
        label: 'Recaudación Ejecutada Real (Bs)',
        data: c3.ejecutado_real_bs,
        borderColor: isDark ? t.goldLight : t.navy,
        backgroundColor: isDark ? t.goldLight : t.navy,
        borderWidth: 2.4,
        pointRadius: 3,
        tension: 0.2,
      },
    ],
  };
}

export function buildCaso4Data(macroData, isDark) {
  const c4 = macroData?.caso4_metas_anuales;
  if (!c4) return null;
  const t = getChartTokens(isDark);
  const hist = c4.valores_historicos_bs || [];
  const proy = c4.proyecciones_ols || [];
  if (hist.length === 0 && proy.length === 0) return null;
  const labels = [...(c4.anios_historicos || []).map(String), ...proy.map((p) => `${p.periodo} (Proy OLS)`)];
  const histData = [...hist, ...Array(proy.length).fill(null)];
  const proyData = hist.length
    ? [...Array(hist.length - 1).fill(null), hist[hist.length - 1], ...proy.map((p) => p.monto_proyectado_bs)]
    : proy.map((p) => p.monto_proyectado_bs);

  return {
    labels,
    datasets: [
      {
        label: 'Recaudación Anual Real (Bs)',
        data: histData,
        borderColor: t.navy,
        backgroundColor: t.navy,
        borderWidth: 2.6,
        pointRadius: 5,
      },
      {
        label: 'Tendencia Lineal OLS (Bs)',
        data: proyData,
        borderColor: t.gold,
        backgroundColor: t.gold,
        borderWidth: 2.6,
        borderDash: [5, 4],
        pointRadius: 5,
      },
    ],
  };
}

export { buildChartOptions };
