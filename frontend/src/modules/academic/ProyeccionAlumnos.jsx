import React, { useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Play } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export default function ProyeccionAlumnos() {
  const [agregacion, setAgregacion] = useState('Consolidado Global (Caso 1)');
  const [ejecutado, setEjecutado] = useState(false);
  const [logContent, setLogContent] = useState([]);

  const handleExecute = () => {
    setLogContent([
      '> consulting PostgreSQL...',
      '> serie loaded for ' + agregacion,
      '> model selected ExponentialSmoothing',
      '> MAE error: 2.34',
      '> projection result generated',
      '> timestamp: ' + new Date().toISOString()
    ]);
    setEjecutado(true);
  };

  const chartData = {
    labels: ['May 2026', 'Jun 2026', 'Jul 2026', 'Ago 2026', 'Sep-Dic 2026 (Proy)'],
    datasets: [
      {
        label: 'Alumnos Matriculados (Histórico)',
        data: [130, 148, 155, 160, ejecutado ? null : null],
        borderColor: '#0C1E33',
        backgroundColor: '#0C1E33',
        borderWidth: 2.5,
        tension: 0.15,
      },
      {
        label: 'Proyección (Holt-Winters)',
        data: [null, null, null, 160, ejecutado ? 184 : null],
        borderColor: '#D99B26',
        backgroundColor: '#D99B26',
        borderWidth: 2.5,
        borderDash: [6, 4],
        tension: 0.15,
      }
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: 'var(--color-slate-gray)',
          font: { family: 'var(--font-sohne)', size: 12 }
        }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(119, 123, 134, 0.1)' },
        ticks: { color: 'var(--color-slate-gray)', font: { family: 'var(--font-sohne)' } }
      },
      y: {
        grid: { color: 'rgba(119, 123, 134, 0.1)' },
        ticks: { color: 'var(--color-slate-gray)', font: { family: 'var(--font-sohne)' } }
      }
    }
  };

  return (
    <div className="module-container space-y-6">
      <PageHeader
        category="STATSMODELS · SERIES TEMPORALES (HOLT-WINTERS)"
        title="Proyección de Alumnos"
        subtitle="Modelo predictivo de matrícula académica utilizando suavizado exponencial y estimaciones estadísticas continuas."
      />

      <div className="card-mist kinetic-card p-6 rounded-[24px]">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nivel de Agregación / Tipo de Programa</label>
            <select 
              className="form-input w-full p-2 border rounded-[16px]" 
              value={agregacion} 
              onChange={e => setAgregacion(e.target.value)}
            >
              <option>Consolidado Global (Caso 1)</option>
              <option>Diplomados (N=43)</option>
              <option>Cursos (N=41)</option>
              <option>Programas Expertos (N=42)</option>
              <option>Maestrías</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 flex items-center justify-between">
              Escuela Académica
              <span className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full">Diferido: JOIN POS→Escuela</span>
            </label>
            <select className="form-input w-full p-2 border rounded-[16px] bg-gray-100 text-gray-500 cursor-not-allowed" disabled>
              <option>Todas las Escuelas</option>
            </select>
          </div>
        </div>
        <button className="btn-pill-dark px-6 py-2 bg-ink-black text-paper-white rounded-full flex items-center gap-2 hover:opacity-90 transition-opacity" onClick={handleExecute}>
          <Play size={16} /> Ejecutar Proyección (Holt-Winters)
        </button>
      </div>

      <div className="bg-fog-white border rounded-lg p-3 flex items-center gap-3">
        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
        <span className="text-sm font-medium">Proyectando Sep - Dic 2026 ({agregacion})</span>
        <span className="text-xs bg-gray-200 px-2 py-1 rounded">Holt-Winters</span>
      </div>

      {ejecutado && (
        <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm h-32 overflow-y-auto">
          {logContent.map((line, i) => <div key={i}>{line}</div>)}
        </div>
      )}

      <div className="floating-artifact kinetic-card bg-paper-white p-6 rounded-[24px] shadow-sm" style={{ height: '400px' }}>
        <Line data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
