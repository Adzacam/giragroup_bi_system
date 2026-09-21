import React from 'react';

export default function RegistroInconsistencias() {
  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '24px' }}>
        <h2 className="serif-heading" style={{ fontFamily: 'Newsreader, serif', fontSize: '24px', color: '#17191c', marginBottom: '8px' }}>
          Registro de Inconsistencias (GIRA-43)
        </h2>
      </header>

      <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px', color: '#4a5568', fontSize: '14px', lineHeight: '1.6' }}>
        Log de excepciones del pipeline en tiempo real. 
        <br/><br/>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#c53030' }}>
          [2026-09-20 10:15:06] ERR_VAL_04: 52 registros exceden umbral de nulidad tolerado en 'Acta_POS_2026_Modulo3.xlsx' (Columna: FECHA_EVAL).
        </span>
      </div>
    </div>
  );
}
