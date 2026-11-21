import React from 'react';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';

export default function GraficoPersonalizadoBody({ tipo, titulo, filas, tokens, chartOpts }) {
  const visibles = (filas || []).filter((f) => !f.oculto);
  if (!visibles.length) {
    return <div className="cmi-pred-empty">Sin grupos con n ≥ 5 registros para mostrar.</div>;
  }

  if (tipo === 'table') {
    return (
      <div tabIndex={0} role="region" aria-label={titulo} className="cmi-table-wrap" style={{ maxHeight: 240, overflow: 'auto' }}>
        <table className="cmi-table">
          <thead>
            <tr>
              <th scope="col">Categoría</th>
              <th scope="col" className="num-col">Valor</th>
              <th scope="col" className="num-col">Registros</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((f, idx) => (
              <tr key={idx}>
                <th scope="row" style={{ fontWeight: 500, textAlign: 'left' }}>{f.etiqueta}</th>
                <td className="num-col">{f.valor ?? '—'}</td>
                <td className="num-col">{f.n_registros}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const isArea = tipo === 'area';
  const isLine = tipo === 'line' || isArea;
  const data = {
    labels: visibles.map((f) => f.etiqueta),
    datasets: [{
      label: titulo,
      data: visibles.map((f) => f.valor ?? 0),
      backgroundColor: tipo === 'doughnut'
        ? [tokens.navy, tokens.gold, tokens.ok, tokens.bad]
        : (isArea ? 'rgba(217, 155, 38, 0.22)' : tokens.gold),
      borderColor: isLine ? tokens.gold : undefined,
      borderWidth: isLine ? 2 : 0,
      fill: isArea,
      tension: isLine ? 0.3 : 0,
      borderRadius: tipo === 'bar' ? 6 : 0,
    }],
  };

  return (
    <ChartRevealV2>
      {tipo === 'doughnut' && (
        <Doughnut data={data} options={{ responsive: true, maintainAspectRatio: false }} plugins={CHART_PLUGINS_V2} />
      )}
      {isLine && (
        <Line data={data} options={chartOpts} plugins={CHART_PLUGINS_V2} />
      )}
      {tipo === 'bar' && (
        <Bar data={data} options={chartOpts} plugins={CHART_PLUGINS_V2} />
      )}
    </ChartRevealV2>
  );
}
