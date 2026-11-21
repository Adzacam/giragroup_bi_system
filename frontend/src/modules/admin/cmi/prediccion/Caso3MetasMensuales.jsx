import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Maximize2 } from 'lucide-react';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';
import { fmtBs } from './chartConfig';

export default function Caso3MetasMensuales({ macroData, chartData, chartOptions, isLoading, onOpenDetail }) {
  const c3 = macroData?.caso3_metas_mensuales;
  const mesActual = c3?.mes_actual;

  return (
    <article className="card-mist kinetic-card heavy-section-deferred cmi-pred-card">
      <div className="cmi-pred-card-head">
        <div>
          <span className="cmi-eyebrow">Caso 3 · Presupuesto Mensual</span>
          <h3 className="cmi-pred-title">Cumplimiento de Metas e Ingresos Mensuales</h3>
        </div>
        <button
          type="button"
          className="cmi-pred-expand"
          onClick={() => onOpenDetail({
            titulo: 'Desglose Longitudinal: Caso 3 (Meta vs Ejecutado)',
            tipo: 'caso3',
            data: c3,
          })}
          title="Expandir tabla completa de metas mensuales"
          aria-label="Expandir tabla completa de metas mensuales"
        >
          <Maximize2 size={16} aria-hidden="true" />
        </button>
      </div>

      {mesActual && (
        <div className="cmi-pred-chips">
          <span className="cmi-chip cmi-chip-muted">
            Meta {mesActual.periodo}: Bs. {fmtBs(mesActual.meta_mes_bs)}
          </span>
          <span className="cmi-chip cmi-chip-gold">
            Cierre HW: Bs. {fmtBs(mesActual.cierre_proyectado_hw_bs)}
          </span>
          <span className="cmi-chip cmi-chip-ok">
            Cumplimiento: {mesActual.cumplimiento_proyectado_pct ?? '—'}%
          </span>
        </div>
      )}

      <div className="cmi-pred-chart-box">
        {chartData ? (
          <ChartRevealV2>
            <Bar data={chartData} options={chartOptions} plugins={CHART_PLUGINS_V2} />
          </ChartRevealV2>
        ) : (
          <div className="cmi-pred-empty">
            {isLoading ? 'Cargando comparativa mensual de metas...' : (macroData?.sin_datos?.caso3 || 'Sin metas ni ejecución financiera en el Data Warehouse.')}
          </div>
        )}
      </div>
    </article>
  );
}
