import React, { useMemo, useState } from 'react';
import { Sparkles } from 'lucide-react';
import usePaginacion from '../../../../hooks/usePaginacion';
import { useTheme } from '../../../../context/ThemeContext';
import CachedSubTabsV2 from '../../../../v2/components/CachedSubTabsV2';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';
import { buildCaso1Data, buildCaso3Data, buildCaso4Data, buildChartOptions } from './chartConfig';
import Caso1Demanda from './Caso1Demanda';
import Caso2Programas from './Caso2Programas';
import Caso3MetasMensuales from './Caso3MetasMensuales';
import Caso4TendenciaAnual from './Caso4TendenciaAnual';
import DetallePrediccion from './DetallePrediccion';

const SUB_TABS = [
  { id: 'demanda', label: 'Demanda' },
  { id: 'programas', label: 'Programas' },
  { id: 'metas', label: 'Metas mensuales' },
  { id: 'anual', label: 'Tendencia anual' },
];

export default function PrediccionPage({
  macroData,
  isLoading,
  horizonte,
  onHorizonteChange,
  onRecalcular,
  searchProg,
  onSearchProgChange,
}) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [subTab, setSubTab] = useState('demanda');
  const [filtroTipoProg, setFiltroTipoProg] = useState('GLOBAL');
  const [modalDetail, setModalDetail] = useState(null);

  const filteredViabilidad = useMemo(() => (
    (macroData?.caso2_demanda_programa?.matriz_viabilidad || []).filter((item) => {
      const matchTipo = filtroTipoProg === 'GLOBAL' || item.tipo.toUpperCase().includes(filtroTipoProg);
      const matchText = searchProg === '' || item.programa.toLowerCase().includes(searchProg.toLowerCase());
      return matchTipo && matchText;
    })
  ), [macroData, filtroTipoProg, searchProg]);
  const pagViab = usePaginacion(filteredViabilidad);

  const chartCaso1Data = useMemo(() => buildCaso1Data(macroData, isDark), [macroData, isDark]);
  const chartCaso3Data = useMemo(() => buildCaso3Data(macroData, isDark), [macroData, isDark]);
  const chartCaso4Data = useMemo(() => buildCaso4Data(macroData, isDark), [macroData, isDark]);
  const chartOptions = useMemo(() => buildChartOptions(isDark), [isDark]);

  const c1 = macroData?.caso1_demanda_global;
  const c3 = macroData?.caso3_metas_mensuales;
  const c4 = macroData?.caso4_metas_anuales;

  const totalProyectado = useMemo(() => {
    if (!c1?.forecast_hw?.length) return null;
    return Math.round(c1.forecast_hw.reduce((s, v) => s + Number(v || 0), 0));
  }, [c1]);

  const icRango = useMemo(() => {
    if (!c1?.ic_lower_95?.length || !c1?.ic_upper_95?.length) return null;
    const inf = Math.round(c1.ic_lower_95.reduce((s, v) => s + Number(v || 0), 0));
    const sup = Math.round(c1.ic_upper_95.reduce((s, v) => s + Number(v || 0), 0));
    return `${inf} – ${sup}`;
  }, [c1]);

  const tabs = useMemo(() => [
    {
      id: 'demanda',
      render: () => (
        <Caso1Demanda
          macroData={macroData}
          chartData={chartCaso1Data}
          chartOptions={chartOptions}
          isLoading={isLoading}
          onOpenDetail={setModalDetail}
        />
      ),
    },
    {
      id: 'programas',
      render: () => (
        <Caso2Programas
          searchProg={searchProg}
          onSearchChange={onSearchProgChange}
          filtroTipoProg={filtroTipoProg}
          onFiltroTipoChange={setFiltroTipoProg}
          pagViab={pagViab}
          onOpenDetail={setModalDetail}
        />
      ),
    },
    {
      id: 'metas',
      render: () => (
        <Caso3MetasMensuales
          macroData={macroData}
          chartData={chartCaso3Data}
          chartOptions={chartOptions}
          isLoading={isLoading}
          onOpenDetail={setModalDetail}
        />
      ),
    },
    {
      id: 'anual',
      render: () => (
        <Caso4TendenciaAnual
          macroData={macroData}
          chartData={chartCaso4Data}
          chartOptions={chartOptions}
          isLoading={isLoading}
          onOpenDetail={setModalDetail}
        />
      ),
    },
  ], [macroData, chartCaso1Data, chartCaso3Data, chartCaso4Data, chartOptions, isLoading, searchProg, onSearchProgChange, filtroTipoProg, pagViab]);

  return (
    <div className="space-y-6">
      <div className="cmi-pred-banner">
        <div>
          <div className="cmi-pred-banner-title">
            <Sparkles size={15} className="cmi-icon-gold" aria-hidden="true" />
            <span>Motor Predictivo: Holt-Winters Amortiguado (damped_trend=True, m=12) &amp; Estimador OLS</span>
          </div>
          <div className="cmi-pred-banner-sub">
            {c1 ? `Serie longitudinal N = ${c1.n_observaciones} meses (${c1.periodos_historicos[0]} – ${c1.periodos_historicos.at(-1)}) · ` : ''}
            Intervalo de Confianza: 95% con cota no negativa (ŷ ≥ 0)
          </div>
        </div>

        <div className="cmi-pred-banner-controls">
          <label htmlFor="cmi-horizonte-select" className="cmi-pred-banner-label">Horizonte:</label>
          <select
            id="cmi-horizonte-select"
            className="cmi-input cmi-select-compact"
            value={horizonte}
            onChange={(e) => onHorizonteChange(Number(e.target.value))}
          >
            <option value={3}>3 meses (Corto Plazo)</option>
            <option value={6}>6 meses (Semestral)</option>
          </select>
          <button
            type="button"
            onClick={onRecalcular}
            disabled={isLoading}
            className="cmi-btn-recalcular"
          >
            {isLoading ? 'Proyectando...' : 'Recalcular'}
          </button>
        </div>
      </div>

      {/* Franja ejecutiva de 4 cards */}
      <div className="cmi-pred-kpi-strip">
        <article className="cmi-card cmi-pred-kpi-card">
          <span className="cmi-eyebrow">Inscritos proyectados ({horizonte} m)</span>
          <strong className="cmi-num">
            {totalProyectado !== null ? <AnimatedNumberV2 value={totalProyectado} /> : '—'}
          </strong>
          <small>{icRango ? `IC 95%: ${icRango} al.` : 'Sin proyección disponible'}</small>
        </article>
        <article className="cmi-card cmi-pred-kpi-card">
          <span className="cmi-eyebrow">Calidad del modelo (hold-out 6 m)</span>
          <strong className="cmi-num">
            {c1?.mape_pct !== undefined ? `${c1.mape_pct}%` : '—'}
          </strong>
          <small>{c1?.rmse !== undefined ? `MAPE · RMSE: ${c1.rmse}` : 'Sin evaluación'}</small>
        </article>
        <article className="cmi-card cmi-pred-kpi-card">
          <span className="cmi-eyebrow">Cumplimiento proyectado del mes</span>
          <strong className="cmi-num">
            {c3?.mes_actual?.cumplimiento_proyectado_pct !== undefined ? `${c3.mes_actual.cumplimiento_proyectado_pct}%` : '—'}
          </strong>
          <small>{c3?.mes_actual?.periodo ? `Periodo ${c3.mes_actual.periodo}` : 'Sin mes en curso'}</small>
        </article>
        <article className="cmi-card cmi-pred-kpi-card">
          <span className="cmi-eyebrow">Avance de la meta anual</span>
          <strong className="cmi-num">
            {c4?.porcentaje_avance_meta !== undefined ? `${c4.porcentaje_avance_meta}%` : '—'}
          </strong>
          <small>{c4?.gestion_actual ? `Gestión ${c4.gestion_actual}` : 'Sin meta anual'}</small>
        </article>
      </div>

      {/* Sub-pestañas con CachedSubTabsV2 */}
      <div className="cmi-chip-group" role="tablist" aria-label="Casos de analítica predictiva">
        {SUB_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={subTab === t.id}
            className={`cmi-filter-chip ${subTab === t.id ? 'is-active' : ''}`}
            onClick={() => setSubTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <CachedSubTabsV2 tabs={tabs} activeTabId={subTab} />

      <DetallePrediccion modalDetail={modalDetail} onClose={() => setModalDetail(null)} />
    </div>
  );
}
