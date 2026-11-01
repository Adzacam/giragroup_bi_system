import React, { useState, useEffect, useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { RefreshCw, TrendingUp, Users, Award, Search, Sparkles, Filter, ChevronRight, Maximize2, X } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import { useTheme } from '../../context/ThemeContext';
import forecastApi from '../../api/forecastApi';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

export default function ProyeccionAlumnos() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [agregacion, setAgregacion] = useState('GLOBAL');
  const [horizonte, setHorizonte] = useState(6);
  const [macroData, setMacroData] = useState(null);
  const [specificForecast, setSpecificForecast] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchProg, setSearchProg] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('TODOS');
  const [modalProgDetail, setModalProgDetail] = useState(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [macro, specific] = await Promise.all([
        forecastApi.getAnaliticaPredictivaMacro(horizonte),
        forecastApi.getForecastAlumnos(agregacion, horizonte)
      ]);
      setMacroData(macro);
      setSpecificForecast(specific?.data);
    } catch (err) {
      console.warn('Error fetching forecast data:', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [agregacion, horizonte]);

  const textColor = isDark ? '#FAF9F6' : '#17191C';
  const mutedTextColor = isDark ? '#9CA3AF' : '#777B86';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

  // Gráfica de Serie Temporal (Caso 1 o Segmento Específico)
  const chartData = useMemo(() => {
    if (!macroData?.caso1_demanda_global) return null;
    const c1 = macroData.caso1_demanda_global;

    let periodosProy = c1.periodos_proyectados;
    let forecastVals = c1.forecast_hw;
    let icLower = c1.ic_lower_95;
    let icUpper = c1.ic_upper_95;

    // Si se seleccionó un segmento particular (Diplomado, Curso, Experto)
    if (agregacion !== 'GLOBAL' && specificForecast?.proyecciones) {
      periodosProy = specificForecast.proyecciones.map(p => p.periodo);
      forecastVals = specificForecast.proyecciones.map(p => p.valor_forecast);
      icLower = specificForecast.proyecciones.map(p => p.ic_lower);
      icUpper = specificForecast.proyecciones.map(p => p.ic_upper);
    }

    const labels = [...c1.periodos_historicos, ...periodosProy];
    const historicalSeries = [...c1.valores_historicos, ...Array(periodosProy.length).fill(null)];

    const lastHist = c1.valores_historicos[c1.valores_historicos.length - 1];
    const hwSeries = [...Array(c1.valores_historicos.length - 1).fill(null), lastHist, ...forecastVals];
    const upperSeries = [...Array(c1.valores_historicos.length - 1).fill(null), lastHist, ...icUpper];
    const lowerSeries = [...Array(c1.valores_historicos.length - 1).fill(null), lastHist, ...icLower];

    return {
      labels,
      datasets: [
        {
          label: `Inscritos Históricos (N=43)`,
          data: historicalSeries,
          borderColor: isDark ? '#FAF9F6' : '#0C1E33',
          backgroundColor: isDark ? '#FAF9F6' : '#0C1E33',
          borderWidth: 2.2,
          pointRadius: 2,
          tension: 0.18,
        },
        {
          label: `Proyección Holt-Winters (${agregacion})`,
          data: hwSeries,
          borderColor: '#D99B26',
          backgroundColor: '#D99B26',
          borderWidth: 2.6,
          borderDash: [6, 4],
          pointRadius: 4,
          tension: 0.18,
        },
        {
          label: 'Banda Confianza 95% Superior',
          data: upperSeries,
          borderColor: 'transparent',
          backgroundColor: 'rgba(217, 155, 38, 0.14)',
          pointRadius: 0,
          fill: '+1',
        },
        {
          label: 'Banda Confianza 95% Inferior (ŷ ≥ 0)',
          data: lowerSeries,
          borderColor: 'transparent',
          backgroundColor: 'rgba(217, 155, 38, 0.14)',
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Tendencia Lineal OLS',
          data: c1.recta_ols_full || [],
          borderColor: '#1B8754',
          borderWidth: 1.5,
          pointRadius: 0,
          borderDash: [2, 3],
          fill: false,
        }
      ]
    };
  }, [macroData, specificForecast, agregacion, isDark]);

  const chartOptions = {
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

  // Filtrado de la Matriz de Viabilidad
  const viabilidadList = (macroData?.caso2_demanda_programa?.matriz_viabilidad || []).filter(item => {
    const matchTipo = filtroTipo === 'TODOS' || item.tipo.toUpperCase().includes(filtroTipo);
    const matchText = searchProg === '' || item.programa.toLowerCase().includes(searchProg.toLowerCase());
    return matchTipo && matchText;
  });

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: '70px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <PageHeader
          category="ÁREA ACADÉMICA · MODELOS PREDICTIVOS MACRO"
          title="Proyección de Alumnos y Demanda"
          italicWord="Académica"
          subtitle="Modelado cuantitativo de matrícula mediante Holt-Winters aditivo (m=12) y Matriz de Viabilidad Estratégica de Cursos."
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
          Actualizar Proyecciones
        </button>
      </div>

      {/* ── Controles de Parametrización y Métricas de Rigor ───────────────── */}
      <div className="card-mist kinetic-card p-6 rounded-[24px] mt-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
              Segmento de Programa
            </label>
            <select
              value={agregacion}
              onChange={e => setAgregacion(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '12px',
                fontSize: '13px',
                fontWeight: 600,
                border: '1px solid var(--color-border)',
                background: 'var(--color-paper-white)',
                color: 'var(--color-ink-black)'
              }}
            >
              <option value="GLOBAL">Consolidado Global (Caso 1)</option>
              <option value="DIPLOMADO">Diplomados (N=9,150)</option>
              <option value="CURSO">Cursos Cortos (N=3,399)</option>
              <option value="EXPERTO">Programas Expertos (N=2,504)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
              Horizonte de Proyección
            </label>
            <select
              value={horizonte}
              onChange={e => setHorizonte(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '12px',
                fontSize: '13px',
                fontWeight: 600,
                border: '1px solid var(--color-border)',
                background: 'var(--color-paper-white)',
                color: 'var(--color-ink-black)'
              }}
            >
              <option value={3}>3 meses futuros</option>
              <option value={6}>6 meses futuros (Semestre proyectado)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
              Tendencia Lineal OLS
            </label>
            <div style={{ padding: '8px 12px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)', fontSize: '13px', fontWeight: 700, color: 'var(--color-alert-green)' }}>
              {macroData?.caso1_demanda_global?.pendiente_ols_mes ?? '—'} alumnos / mes
            </div>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
              Precisión del Modelo (MAPE / RMSE)
            </label>
            <div style={{ padding: '8px 12px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)', fontSize: '13px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>
              MAPE: {macroData?.caso1_demanda_global?.mape_pct ?? '—'}% · RMSE: {macroData?.caso1_demanda_global?.rmse ?? '—'}
            </div>
          </div>
        </div>

        {/* Gráfico Caso 1 */}
        <div style={{ height: '320px' }}>
          {chartData ? (
            <Line data={chartData} options={chartOptions} />
          ) : (
            <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
              Calculando proyecciones con Holt-Winters...
            </div>
          )}
        </div>
      </div>

      {/* ── Sección Caso 2: Matriz de Viabilidad Estratégica de Cursos ──────── */}
      <div className="card-mist kinetic-card p-6 rounded-[24px] mt-6">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
              Caso 2 · Portafolio Académico
            </span>
            <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
              Matriz de Viabilidad de Cursos (Foco Marketing)
            </h3>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', width: '220px' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--color-slate-gray)' }} />
              <input
                type="text"
                placeholder="Buscar programa..."
                value={searchProg}
                onChange={e => setSearchProg(e.target.value)}
                style={{
                  width: '100%',
                  padding: '7px 10px 7px 32px',
                  borderRadius: '10px',
                  fontSize: '12px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-paper-white)',
                  color: 'var(--color-ink-black)'
                }}
              />
            </div>
            <select
              value={filtroTipo}
              onChange={e => setFiltroTipo(e.target.value)}
              style={{
                padding: '7px 12px',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: 600,
                border: '1px solid var(--color-border)',
                background: 'var(--color-paper-white)',
                color: 'var(--color-ink-black)'
              }}
            >
              <option value="TODOS">Todas las Modalidades</option>
              <option value="DIPLOMADO">Diplomados</option>
              <option value="CURSO">Cursos</option>
              <option value="EXPERTO">Expertos</option>
              <option value="MAESTR">Maestrías</option>
            </select>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                <th style={{ padding: '10px' }}>Nombre del Programa</th>
                <th style={{ padding: '10px' }}>Tipo</th>
                <th style={{ padding: '10px' }}>Inscritos Históricos</th>
                <th style={{ padding: '10px' }}>CAGR (%)</th>
                <th style={{ padding: '10px' }}>Proyección 6m</th>
                <th style={{ padding: '10px' }}>Tendencia</th>
                <th style={{ padding: '10px' }}>Recomendación Estratégica</th>
              </tr>
            </thead>
            <tbody>
              {viabilidadList.map((item, idx) => (
                <tr
                  key={idx}
                  onClick={() => setModalProgDetail(item)}
                  style={{
                    borderBottom: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease'
                  }}
                  className="hover:bg-black/5 dark:hover:bg-white/5"
                  title="Haga clic para ver el desglose analítico completo"
                >
                  <td style={{ padding: '12px 10px', fontWeight: 600, maxWidth: '280px' }}>{item.programa}</td>
                  <td style={{ padding: '12px 10px' }}>
                    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '6px', background: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                      {item.tipo}
                    </span>
                  </td>
                  <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>{item.total_historico}</td>
                  <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: item.cagr_pct >= 0 ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                    {item.cagr_pct > 0 ? `+${item.cagr_pct}%` : `${item.cagr_pct}%`}
                  </td>
                  <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{item.proyeccion_6m} alumnos</td>
                  <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>{item.tendencia_ols}</td>
                  <td style={{ padding: '12px 10px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '3px 10px',
                        borderRadius: '9999px',
                        whiteSpace: 'nowrap',
                        background: item.badge_color === 'emerald' ? 'rgba(27,135,84,0.14)' : (item.badge_color === 'amber' ? 'rgba(217,155,38,0.14)' : 'rgba(217,56,58,0.14)'),
                        color: item.badge_color === 'emerald' ? 'var(--color-alert-green)' : (item.badge_color === 'amber' ? 'var(--color-gira-gold)' : 'var(--color-alert-red)'),
                      }}
                    >
                      {item.decision_sugerida}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Detalle de Programa */}
      {modalProgDetail && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(12, 30, 51, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px'
          }}
          onClick={() => setModalProgDetail(null)}
        >
          <div
            style={{
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '24px',
              maxWidth: '750px',
              width: '100%',
              maxHeight: '85vh',
              overflowY: 'auto',
              padding: '28px',
              border: '1px solid var(--color-border)',
              boxShadow: 'var(--shadow-modal)'
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                  Evaluación Estratégica de Oferta Académica
                </span>
                <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                  {modalProgDetail.programa}
                </h3>
              </div>
              <button
                onClick={() => setModalProgDetail(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 10px', borderRadius: '9999px', background: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                {modalProgDetail.tipo}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '3px 10px',
                  borderRadius: '9999px',
                  background: modalProgDetail.badge_color === 'emerald' ? 'rgba(27,135,84,0.14)' : (modalProgDetail.badge_color === 'amber' ? 'rgba(217,155,38,0.14)' : 'rgba(217,56,58,0.14)'),
                  color: modalProgDetail.badge_color === 'emerald' ? 'var(--color-alert-green)' : (modalProgDetail.badge_color === 'amber' ? 'var(--color-gira-gold)' : 'var(--color-alert-red)'),
                }}
              >
                {modalProgDetail.decision_sugerida}
              </span>
            </div>

            <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-mist-gray)', marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-ink-black)', marginBottom: '4px' }}>
                Dictamen y Recomendación de Marketing:
              </div>
              <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: 1.5 }}>
                {modalProgDetail.justificacion}
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos Históricos</div>
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalProgDetail.total_historico}</div>
              </div>
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos 2025</div>
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalProgDetail.inscritos_2025}</div>
              </div>
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos 2026</div>
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalProgDetail.inscritos_2026}</div>
              </div>
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>CAGR</div>
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)', color: modalProgDetail.cagr_pct >= 0 ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                  {modalProgDetail.cagr_pct > 0 ? `+${modalProgDetail.cagr_pct}%` : `${modalProgDetail.cagr_pct}%`}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Proyección 6 Meses</div>
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)', color: 'var(--color-gira-gold)' }}>
                  {modalProgDetail.proyeccion_6m} al.
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Pendiente OLS</div>
                <div style={{ fontSize: '17px', fontWeight: 700, marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  {modalProgDetail.tendencia_ols}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
