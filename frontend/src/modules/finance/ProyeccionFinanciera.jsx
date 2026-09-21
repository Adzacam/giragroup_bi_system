import React, { useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Play } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export default function ProyeccionFinanciera() {
  const [alcance, setAlcance] = useState('global');
  const [horizonte, setHorizonte] = useState('Q_HW');
  const [categoria, setCategoria] = useState('PROGRAMAS');
  const [ejecutado, setEjecutado] = useState(false);

  const handleExecute = () => {
    setEjecutado(true);
  };

  const isGlobal = alcance === 'global';

  const chartData = {
    labels: ['Q1 2025', 'Q2 2025', 'Q3 2025', 'Q4 2025', 'Q1 2026', 'Q2 2026 (Proy)'],
    datasets: [
      {
        label: 'Cobrado Real ($k)',
        data: [280, 310, 340, 360, 380, ejecutado ? null : null],
        borderColor: '#17191c',
        backgroundColor: '#17191c',
        borderWidth: 2,
        tension: 0.1,
      },
      {
        label: 'Pronóstico Flujo ($k)',
        data: [null, null, null, null, 380, ejecutado ? 412 : null],
        borderColor: '#1b8754',
        backgroundColor: '#1b8754',
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.1,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } }
  };

  const getModeText = () => {
    if (isGlobal && horizonte.includes('HW')) return "Modo A: ExponentialSmoothing(trend='add', seasonal='add')";
    if (isGlobal && !horizonte.includes('HW')) return "Modo A: statsmodels OLS (Regresión Lineal)";
    if (!isGlobal && horizonte.includes('HW')) return `Modo B: ExponentialSmoothing for [${categoria}]`;
    return `Modo B: OLS for [${categoria}]`;
  };

  return (
    <div className="module-container space-y-6">
      <header>
        <span className="subtitle text-xs uppercase tracking-widest text-mist-gray">statsmodels · Proyección Financiera</span>
        <h2 className="serif-display text-ink-black mt-2" style={{ fontSize: '38px' }}>Proyección Financiera y Metas</h2>
      </header>

      <div className="card-mist kinetic-card p-6 rounded-[24px] space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Selector de Alcance</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input type="radio" name="alcance" value="global" checked={isGlobal} onChange={() => setAlcance('global')} />
              Consolidado Empresa (Caja General - Caso 5)
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="alcance" value="cat" checked={!isGlobal} onChange={() => setAlcance('cat')} />
              Por Categoría de Meta (Caso 6)
            </label>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Horizonte Temporal</label>
            <select className="form-input w-full p-2 border rounded-[16px]" value={horizonte} onChange={(e) => setHorizonte(e.target.value)}>
              <option value="M_HW">Próximo Mes (Holt-Winters)</option>
              <option value="Q_HW">Próximo Trimestre (Holt-Winters)</option>
              <option value="Y_OLS">Siguiente Gestión / Anual (OLS)</option>
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium mb-1 ${isGlobal ? 'opacity-40' : ''}`}>Categoría de Meta</label>
            <select className="form-input w-full p-2 border rounded-[16px]" disabled={isGlobal} style={{ opacity: isGlobal ? 0.4 : 1 }} value={categoria} onChange={(e) => setCategoria(e.target.value)}>
              <option>PROGRAMAS</option>
              <option>TECHOS_CERRADOS</option>
            </select>
          </div>
        </div>

        <button className="btn-pill-dark px-6 py-2 bg-ink-black text-paper-white rounded-full flex items-center gap-2 hover:opacity-90 transition-opacity" onClick={handleExecute}>
          <Play size={16} /> Generar Proyección Financiera
        </button>
      </div>

      <div className="bg-fog-white border rounded-lg p-3 text-sm font-medium">
        {getModeText()}
      </div>

      {ejecutado && (
        <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm h-32 overflow-y-auto">
          {'>'} Iniciando cálculo de proyección...<br/>
          {'>'} Generando predicciones...<br/>
          {'>'} Resultados generados exitosamente.
        </div>
      )}

      <div className="floating-artifact kinetic-card bg-paper-white p-6 rounded-[24px] shadow-sm" style={{ height: '400px' }}>
        <Line data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
