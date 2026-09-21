import React from 'react';

export default function RecaudacionCobranzas() {
  return (
    <div className="module-container">
      <header className="mb-6">
        <span className="subtitle text-xs uppercase tracking-widest text-mist-gray">ANALISTA_FINANCIERO</span>
        <h2 className="serif-display text-ink-black mt-2" style={{ fontSize: '40px' }}>Panel de Cobranzas y Recaudación</h2>
      </header>
      <div className="card-mist p-6 rounded-[24px]">
        <p className="serif-display text-ink-black" style={{ fontSize: '34px' }}>$348,290 USD</p>
        <p className="text-green-600 font-medium mt-2">↑ 12.4% vs meta mensual</p>
      </div>
    </div>
  );
}
