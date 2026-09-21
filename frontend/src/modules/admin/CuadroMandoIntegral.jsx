import React from 'react';

export default function CuadroMandoIntegral() {
  return (
    <div className="module-container">
      <header className="mb-8">
        <span className="subtitle text-xs uppercase tracking-widest text-mist-gray">ADMINISTRACIÓN TOTAL</span>
        <h2 className="serif-display text-ink-black mt-2" style={{ fontSize: '40px' }}>Cuadro de Mando Integral Ejecutivo</h2>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card-mist p-6 rounded-[24px] relative">
          <span className="absolute top-4 right-4 text-xs font-bold text-sienna-brown uppercase">1. Financiera</span>
          <p className="serif-display text-ink-black mt-4" style={{ fontSize: '28px' }}>$1,420 USD</p>
          <p className="text-green-600 font-medium">Ticket promedio (104% meta)</p>
        </div>

        <div className="card-mist p-6 rounded-[24px] relative">
          <span className="absolute top-4 right-4 text-xs font-bold text-sienna-brown uppercase">2. Académica</span>
          <p className="serif-display text-ink-black mt-4" style={{ fontSize: '28px' }}>94.8% Retención</p>
          <p className="text-gray-600">24 estudiantes en alerta</p>
        </div>

        <div className="card-mist p-6 rounded-[24px] relative">
          <span className="absolute top-4 right-4 text-xs font-bold text-sienna-brown uppercase">3. Procesos DataOps</span>
          <p className="serif-display text-ink-black mt-4" style={{ fontSize: '28px' }}>98.1% Limpios</p>
          <p className="text-green-600 font-medium">Inferencia BETO nominal</p>
        </div>
      </div>
    </div>
  );
}
