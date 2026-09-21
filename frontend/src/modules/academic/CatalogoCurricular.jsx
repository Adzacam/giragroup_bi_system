import React from 'react';

export default function CatalogoCurricular() {
  return (
    <div className="module-container">
      <header className="mb-6">
        <h2 className="serif-heading text-ink-black" style={{ fontSize: '34px' }}>Catálogo Curricular y Actas</h2>
      </header>
      <div className="floating-artifact bg-paper-white p-6 rounded-[24px] shadow-sm">
        <h3 className="font-semibold text-lg text-ink-black">POS-101: Maestría en Dirección y Gestión Empresarial</h3>
        <p className="text-gray-600 mt-1">24 actas consolidadas</p>
      </div>
    </div>
  );
}
