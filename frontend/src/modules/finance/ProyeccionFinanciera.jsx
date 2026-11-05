import React, { useState, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { RefreshCw, DollarSign, Target, TrendingUp, Calendar, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import { useTheme } from '../../context/ThemeContext';
import forecastApi from '../../api/forecastApi';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler);

export default function ProyeccionFinanciera() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [horizonte, setHorizonte] = useState(6);
  const [granularidad, setGranularidad] = useState('MENSUAL');

  const {
    data: queryData,
    isLoading,
    refetch: fetchData,
  } = useQuery({
    queryKey: ['finance', 'proyeccion-financiera', horizonte, granularidad],
    queryFn: async () => {
      const macro = await forecastApi.getAnaliticaPredictivaMacro(horizonte);
      const metas = granularidad === 'MENSUAL'
        ? macro?.caso3_metas_mensuales
        : await forecastApi.getForecastMetas(granularidad, horizonte);
      return {
        macroData: macro,
        metasForecast: metas?.data || metas,
      };
    },
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });

  const macroData = queryData?.macroData || null;
  const metasForecast = queryData?.metasForecast || null;

  const textColor = isDark ? '#FAF9F6' : '#17191C';
  const mutedTextColor = isDark ? '#9CA3AF' : '#777B86';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

  // Gráfica Caso 3: Metas Mensuales vs Recaudación Ejecutada y Holt-Winters
  const chartMensualData = useMemo(() => {
    if (!macroData?.caso3_metas_mensuales) return null;
    const c3 = macroData.caso3_metas_mensuales;
    const etiquetas = c3.meses_etiquetas || [];

    return {
      labels: etiquetas,
      datasets: [
        {
          type: 'bar',
          label: 'Meta Presupuestaria de Catálogo (Bs)',
          data: c3.meta_catalogo_bs,
          backgroundColor: isDark ? 'rgba(119, 123, 134, 0.35)' : 'rgba(12, 30, 51, 0.18)',
          borderColor: isDark ? '#9CA3AF' : '#0C1E33',
          borderWidth: 1,
          borderRadius: 6,
        },
        {
          type: 'line',
          label: 'Recaudación Ejecutada Real (Bs)',
          data: c3.ejecutado_real_bs,
          borderColor: isDark ? '#F1B844' : '#0C1E33',
          backgroundColor: isDark ? '#F1B844' : '#0C1E33',
          borderWidth: 2.5,
          pointRadius: 3,
          tension: 0.2,
        }
      ]
    };
  }, [macroData, isDark]);

  // Gráfica Caso 4: Tendencia Anual OLS vs Meta Institucional
  const chartAnualData = useMemo(() => {
    if (!macroData?.caso4_metas_anuales) return null;
    const c4 = macroData.caso4_metas_anuales;
    const hist = c4.valores_historicos_bs || [];
    const proy = c4.proyecciones_ols || [];
    if (hist.length === 0 && proy.length === 0) return null;
    const labels = [...(c4.anios_historicos || []).map(String), ...proy.map(p => `${p.periodo} (Proy OLS)`)];
    const histData = [...hist, ...Array(proy.length).fill(null)];
    const proyData = hist.length
      ? [...Array(hist.length - 1).fill(null), hist[hist.length - 1], ...proy.map(p => p.monto_proyectado_bs)]
      : proy.map(p => p.monto_proyectado_bs);

    return {
      labels,
      datasets: [
        {
          label: 'Recaudación Histórica Ejecutada (Bs)',
          data: histData,
          borderColor: isDark ? '#FAF9F6' : '#0C1E33',
          backgroundColor: isDark ? '#FAF9F6' : '#0C1E33',
          borderWidth: 2.6,
          pointRadius: 5,
        },
        {
          label: 'Tendencia Interanual OLS (Bs)',
          data: proyData,
          borderColor: '#D99B26',
          backgroundColor: '#D99B26',
          borderWidth: 2.6,
          borderDash: [5, 4],
          pointRadius: 5,
        }
      ]
    };
  }, [macroData, isDark]);

  const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 11 } }
      },
      tooltip: {
        backgroundColor: isDark ? '#20252E' : '#0C1E33',
        titleColor: '#FAF9F6',
        bodyColor: '#FAF9F6',
        padding: 10,
        borderRadius: 8,
      }
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 10 } } },
      y: { grid: { color: gridColor }, ticks: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 10 } } }
    }
  };

  const mesAct = macroData?.caso3_metas_mensuales?.mes_actual;
  const anualAct = macroData?.caso4_metas_anuales;
  // Sin dato del backend se muestra "—": nunca una cifra de relleno
  const sinDato = (v) => v === null || v === undefined || Number.isNaN(Number(v));
  const bs = (v) => (sinDato(v) ? '—' : Math.round(Number(v)).toLocaleString('es-BO'));
  const pct = (v) => (sinDato(v) ? '—' : `${v}%`);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: '70px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <PageHeader
          category="ÁREA FINANCIERA · MODELOS PREDICTIVOS MACRO"
          title="Proyección Financiera y Metas"
          italicWord="Institucionales"
          subtitle="Proyección econométrica de recaudación y flujos de caja mediante Holt-Winters aditivo (m=12) y ajuste lineal plurianual OLS."
        />
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="btn-academic"
          style={{
            marginTop: '24px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '9px 16px',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            borderRadius: '9999px',
            border: '1px solid var(--color-border)',
            background: 'var(--color-paper-white)',
            color: 'var(--color-ink-black)',
          }}
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Actualizar Modelos
        </button>
      </div>

      {/* ── KPIs Principales de Proyección ─────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <div style={{ padding: '18px', borderRadius: '20px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Meta Mes Actual</div>
          <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px' }}>Bs. {bs(mesAct?.meta_mes_bs)}</div>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>Catálogo Oficial de Programas</div>
        </div>

        <div style={{ padding: '18px', borderRadius: '20px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Cierre Proyectado HW</div>
          <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px', color: 'var(--color-gira-gold)' }}>
            Bs. {bs(mesAct?.cierre_proyectado_hw_bs)}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-alert-green)', marginTop: '2px', fontWeight: 600 }}>
            {pct(mesAct?.cumplimiento_proyectado_pct)} de cumplimiento estimado
          </div>
        </div>

        <div style={{ padding: '18px', borderRadius: '20px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Meta Anual Institucional</div>
          <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px' }}>Bs. {bs(anualAct?.meta_anual_institucional_bs)}</div>
          <div style={{ fontSize: '12px', color: 'var(--color-gira-gold)', marginTop: '2px', fontWeight: 600 }}>
            {pct(anualAct?.porcentaje_avance_meta)} ejecutado a la fecha
          </div>
        </div>

        <div style={{ padding: '18px', borderRadius: '20px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Ritmo de Crecimiento OLS</div>
          <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px', color: 'var(--color-alert-green)' }}>
            Bs. {sinDato(anualAct?.pendiente_anual_bs) ? '—' : Math.round(anualAct.pendiente_anual_bs / 1000)}k / año
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
            CAGR Interanual: {pct(anualAct?.cagr_historico_pct)}
          </div>
        </div>
      </div>

      {/* ── Casos 3 y 4: Gráficas de Metas Mensuales y Anuales ───────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        
        {/* Caso 3 */}
        <div className="card-mist kinetic-card p-6 rounded-[24px]">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Caso 3 · Horizonte Mensual
              </span>
              <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                Recaudación Mensual vs Metas Presupuestarias
              </h3>
            </div>
          </div>

          <div style={{ height: '300px' }}>
            {chartMensualData ? (
              <Bar data={chartMensualData} options={defaultChartOptions} />
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
                {isLoading ? 'Cargando datos presupuestarios mensuales...' : (macroData?.sin_datos?.caso3 || 'Sin metas ni ejecución financiera en el Data Warehouse.')}
              </div>
            )}
          </div>
        </div>

        {/* Caso 4 */}
        <div className="card-mist kinetic-card p-6 rounded-[24px]">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Caso 4 · Meta Institucional Anual
              </span>
              <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                Trayectoria Anual Plurianual (OLS)
              </h3>
            </div>
          </div>

          {/* Medidor de Avance Bullet */}
          {anualAct && (
            <div style={{ marginBottom: '16px', padding: '12px 14px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', fontWeight: 600, marginBottom: '6px' }}>
                <span>Meta {anualAct.gestion_actual}: Bs. {bs(anualAct.meta_anual_institucional_bs)}</span>
                <span style={{ color: 'var(--color-gira-gold)', fontWeight: 700 }}>
                  {pct(anualAct.porcentaje_avance_meta)} acumulado (Bs. {bs(anualAct.recaudado_acumulado_bs)})
                </span>
              </div>
              <div style={{ height: '10px', width: '100%', background: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${Math.min(100, anualAct.porcentaje_avance_meta ?? 0)}%`, background: 'linear-gradient(90deg, var(--color-gira-navy), var(--color-gira-gold))', borderRadius: '9999px' }} />
              </div>
            </div>
          )}

          <div style={{ height: '230px' }}>
            {chartAnualData ? (
              <Line data={chartAnualData} options={defaultChartOptions} />
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
                {isLoading ? 'Cargando serie anual OLS...' : (macroData?.sin_datos?.caso4 || anualAct?.nota_metodologica || 'Sin recaudación anual en el Data Warehouse.')}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
