import React from 'react';

export default function EntidadesNoResueltas() {
  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '32px' }}>
        <h2 className="serif-heading" style={{ fontFamily: 'Newsreader, serif', fontSize: '24px', color: '#17191c', marginBottom: '8px' }}>
          Entidades No Resueltas (RapidFuzz)
        </h2>
        <p style={{ color: '#4a5568', fontSize: '14px' }}>
          Sugerencias de mapeo al catálogo canónico para entidades con ambigüedad.
        </p>
      </header>

      <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '24px', padding: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <table className="steep-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#4a5568' }}>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Cadena Detectada</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Entidad Canónica Sugerida</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Score</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #f7fafc' }}>
              <td style={{ padding: '16px 12px', fontFamily: 'JetBrains Mono, monospace', color: '#4a5568', fontSize: '13px' }}>
                "Dr. Carlos Alberto Gomez M."
              </td>
              <td style={{ padding: '16px 12px', fontWeight: '500', color: '#2b6cb0' }}>
                Dr. Carlos A. Gómez Murillo (DOC-109)
              </td>
              <td style={{ padding: '16px 12px' }}>
                <span style={{ backgroundColor: '#fefcbf', color: '#b7791f', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '600' }}>
                  88%
                </span>
              </td>
              <td style={{ padding: '16px 12px' }}>
                <button className="btn-pill-dark" style={{ backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '6px 16px', border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: '500' }}>
                  Vincular
                </button>
              </td>
            </tr>
            <tr>
              <td style={{ padding: '16px 12px', fontFamily: 'JetBrains Mono, monospace', color: '#4a5568', fontSize: '13px' }}>
                "Gest. Datos / Mod 3"
              </td>
              <td style={{ padding: '16px 12px', fontWeight: '500', color: '#2b6cb0' }}>
                MOD-302: Gestión de Datos (Posgrado)
              </td>
              <td style={{ padding: '16px 12px' }}>
                <span style={{ backgroundColor: '#fefcbf', color: '#b7791f', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '600' }}>
                  92%
                </span>
              </td>
              <td style={{ padding: '16px 12px' }}>
                <button className="btn-pill-dark" style={{ backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '6px 16px', border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: '500' }}>
                  Vincular
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
