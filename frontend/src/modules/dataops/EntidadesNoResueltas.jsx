import React from 'react';
import ResponsiveTable from '../../components/shared/ResponsiveTable';

export default function EntidadesNoResueltas() {
  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '11.5px', fontWeight: '600', letterSpacing: '0.08em', color: 'var(--color-slate-gray)', margin: '0 0 8px 0' }}>
          DataOps · Inferencia Difusa
        </p>
        <h2 className="serif-display" style={{ fontSize: 'clamp(28px, 3.5vw, 36px)', margin: '0 0 12px 0', color: 'var(--color-ink-black)' }}>
          Entidades No Resueltas (RapidFuzz)
        </h2>
        <p style={{ color: 'var(--color-slate-gray)', fontSize: '14.5px', margin: 0, maxWidth: '700px' }}>
          Sugerencias de mapeo al catálogo canónico para entidades con ambigüedad o discrepancias de sintaxis.
        </p>
      </header>

      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cadena Detectada</th>
              <th>Entidad Canónica Sugerida</th>
              <th>Score Coincidencia</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                "Dr. Carlos Alberto Gomez M."
              </td>
              <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                Dr. Carlos A. Gómez Murillo <span style={{ color: 'var(--color-slate-gray)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>(DOC-109)</span>
              </td>
              <td>
                <span className="badge-status badge-status-processing">
                  88%
                </span>
              </td>
              <td>
                <button type="button" className="btn-pill-dark" style={{ padding: '6px 16px', fontSize: '12.5px' }}>
                  Vincular
                </button>
              </td>
            </tr>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                "Gest. Datos / Mod 3"
              </td>
              <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                MOD-302: Gestión de Datos <span style={{ color: 'var(--color-slate-gray)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>(Posgrado)</span>
              </td>
              <td>
                <span className="badge-status badge-status-completed">
                  92%
                </span>
              </td>
              <td>
                <button type="button" className="btn-pill-dark" style={{ padding: '6px 16px', fontSize: '12.5px' }}>
                  Vincular
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
