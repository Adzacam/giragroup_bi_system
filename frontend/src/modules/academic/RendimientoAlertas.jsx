import React from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { AlertCircle, CheckCircle } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function RendimientoAlertas() {
  const chartData = {
    labels: ['0-50', '51-70 (Riesgo)', '71-80', '81-90', '91-100'],
    datasets: [
      {
        data: [6, 24, 98, 210, 142],
        backgroundColor: ['#d9383a', '#D99B26', '#F1B844', '#0C1E33', '#1b8754'],
        borderRadius: 8,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(119, 123, 134, 0.1)' },
        ticks: { color: 'var(--color-slate-gray)', font: { family: 'var(--font-sohne)' } }
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(119, 123, 134, 0.1)' },
        ticks: { color: 'var(--color-slate-gray)', font: { family: 'var(--font-sohne)' } }
      },
    },
  };

  return (
    <div className="module-container space-y-6">
      <header>
        <span className="subtitle text-xs uppercase tracking-widest text-mist-gray">DIRECTOR_ACADEMICO · Retención</span>
        <h2 className="serif-display text-ink-black mt-2" style={{ fontSize: '40px' }}>Rendimiento y Alertas de Riesgo</h2>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card-mist kinetic-card p-6 rounded-[24px]">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="text-green-600" size={24} />
            <h3 className="font-semibold text-lg text-ink-black">Tasa Global de Aprobación</h3>
          </div>
          <p className="serif-display text-green-700" style={{ fontSize: '36px' }}>86.4%</p>
        </div>
        
        <div className="card-mist kinetic-card p-6 rounded-[24px]">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="text-red-600" size={24} />
            <h3 className="font-semibold text-lg text-ink-black">Estudiantes en Riesgo (≤ 70)</h3>
          </div>
          <p className="serif-display text-red-600" style={{ fontSize: '36px' }}>24</p>
        </div>
      </div>

      <div className="floating-artifact kinetic-card bg-paper-white p-6 rounded-[24px] shadow-sm">
        <h3 className="font-medium text-lg mb-4 text-ink-black">Distribución de Calificaciones</h3>
        <div style={{ height: '300px' }}>
          <Bar data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}
