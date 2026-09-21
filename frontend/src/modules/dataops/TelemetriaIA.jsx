import React from 'react';

export default function TelemetriaIA() {
  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '24px' }}>
        <h2 className="serif-heading" style={{ fontFamily: 'Newsreader, serif', fontSize: '24px', color: '#17191c', marginBottom: '8px' }}>
          Telemetría y Rendimiento IA (GIRA-12)
        </h2>
      </header>

      <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '32px', borderRadius: '24px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'Newsreader, serif', fontSize: '32px', color: '#17191c', marginBottom: '12px' }}>
          1.42 seg / lote
        </div>
        <div style={{ display: 'inline-block', backgroundColor: '#c6f6d5', color: '#276749', padding: '6px 12px', borderRadius: '9999px', fontSize: '13px', fontWeight: '500' }}>
          Aceleración CUDA 12.2 en contenedor Docker
        </div>
      </div>
    </div>
  );
}
