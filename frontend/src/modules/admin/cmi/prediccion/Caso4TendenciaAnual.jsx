import React from 'react';
import { Line } from 'react-chartjs-2';
import { Maximize2 } from 'lucide-react';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';
import { fmtBs } from './chartConfig';

export default function Caso4TendenciaAnual({ macroData, chartData, chartOptions, isLoading, onOpenDetail }) {
  const c4 = macroData?.caso4_metas_anuales;

  return (
    <article className="card-mist kinetic-card heavy-section-deferred cmi-pred-card">
      <div className="cmi-pred-card-head">
        <div>
          <span className="cmi-eyebrow">Caso 4 · Planificación Plurianual</span>
          <h3 className="cmi-pred-title">Cumplimiento de Meta Anual &amp; Recta OLS</h3>
          <span className="cmi-chip cmi-chip-muted cmi-ols-badge">OLS anual — solo descriptiva</span>
        </div>
        <button
          type="button"
          className="cmi-pred-expand"
          onClick={(e) => onOpenDetail({
            titulo: 'Desglose Plurianual: Caso 4 (Trayectoria OLS hacia la Meta Anual)',
            tipo: 'caso4',
            data: c4,
            triggerEl: e.currentTarget,
          })}
          title="Expandir detalle plurianual OLS"
          aria-label="Expandir detalle plurianual OLS"
        >
          <Maximize2 size={16} aria-hidden="true" />
        </button>
      </div>

      {c4 && (
        <div className="cmi-pred-bullet-box">
          <div className="cmi-pred-bullet-top">
            <span>Meta {c4.gestion_actual}: Bs. {fmtBs(c4.meta_anual_institucional_bs)}</span>
            <span className="cmi-text-gold">
              {c4.porcentaje_avance_meta ?? '—'}% ejecutado (Bs. {fmtBs(c4.recaudado_acumulado_bs)})
            </span>
          </div>
          <div className="cmi-pred-bullet-track">
            <div
              className="cmi-pred-bullet-fill"
              style={{ width: `${Math.min(100, c4.porcentaje_avance_meta ?? 0)}%` }}
            />
          </div>
          <div className="cmi-pred-bullet-foot">
            <span>Pendiente OLS: Bs. {fmtBs(c4.pendiente_anual_bs)}/año</span>
            <span>CAGR Histórica: {c4.cagr_historico_pct ?? '—'}%</span>
          </div>
        </div>
      )}

      <div className="cmi-pred-chart-box cmi-pred-chart-box-sm">
        {chartData ? (
          <ChartRevealV2>
            <Line data={chartData} options={chartOptions} plugins={CHART_PLUGINS_V2} />
          </ChartRevealV2>
        ) : (
          <div className="cmi-pred-empty">
            {isLoading ? 'Cargando tendencia anual...' : (macroData?.sin_datos?.caso4 || c4?.nota_metodologica || 'Sin recaudación anual en el Data Warehouse.')}
          </div>
        )}
      </div>
    </article>
  );
}
