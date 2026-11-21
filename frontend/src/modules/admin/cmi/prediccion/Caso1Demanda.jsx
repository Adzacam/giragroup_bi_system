import React from 'react';
import { Line } from 'react-chartjs-2';
import { Maximize2 } from 'lucide-react';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';

export default function Caso1Demanda({ macroData, chartData, chartOptions, isLoading, onOpenDetail }) {
  const c1 = macroData?.caso1_demanda_global;

  return (
    <article className="card-mist kinetic-card cmi-pred-card">
      <div className="cmi-pred-card-head">
        <div>
          <span className="cmi-eyebrow">Caso 1 · Demanda Académica</span>
          <h3 className="cmi-pred-title">Demanda Global de Alumnos (Matrícula)</h3>
        </div>
        <button
          type="button"
          className="cmi-pred-expand"
          onClick={() => onOpenDetail({
            titulo: `Detalle Longitudinal: Caso 1 (N=${c1?.n_observaciones ?? 0} meses)`,
            tipo: 'caso1',
            data: c1,
          })}
          title="Expandir tabla histórica completa"
          aria-label="Expandir tabla histórica de Demanda Global"
        >
          <Maximize2 size={16} aria-hidden="true" />
        </button>
      </div>

      {c1 && (
        <div className="cmi-pred-chips">
          <span className="cmi-chip cmi-chip-ok">Tendencia OLS: {c1.pendiente_ols_mes} al/mes</span>
          <span className="cmi-chip cmi-chip-gold">CAGR: {c1.cagr_historico_pct}%</span>
          <span className="cmi-chip cmi-chip-muted">MAPE: {c1.mape_pct}% · RMSE: {c1.rmse}</span>
        </div>
      )}

      <div className="cmi-pred-chart-box">
        {chartData ? (
          <ChartRevealV2>
            <Line data={chartData} options={chartOptions} plugins={CHART_PLUGINS_V2} />
          </ChartRevealV2>
        ) : (
          <div className="cmi-pred-empty">
            {isLoading ? 'Cargando serie temporal histórica...' : (macroData?.sin_datos?.caso1 || 'Sin datos de inscripciones en el Data Warehouse.')}
          </div>
        )}
      </div>
    </article>
  );
}
