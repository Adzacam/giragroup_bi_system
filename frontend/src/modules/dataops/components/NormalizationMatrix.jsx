import React from 'react';
import ResponsiveTable from '../../../components/shared/ResponsiveTable';

export default function NormalizationMatrix({ matrix }) {
  const defaultEntries = [
    { o: 'NOMBRES Y APELLIDOS', n: 'nombre_completo', t: 'VARCHAR', r: 'Mapeo directo' },
    { o: 'CALIF_FINAL', n: 'nota_final', t: 'NUMERIC', r: 'Conversión a float' },
    { o: 'DOC_IDENTIDAD/CI', n: 'ci_estudiante', t: 'VARCHAR', r: 'Limpieza alfanumérica' },
    { o: 'COD_MODULO', n: 'codigo_modulo', t: 'VARCHAR', r: 'Mapeo directo' },
    { o: 'FECHA_EVAL', n: 'fecha_asentamiento', t: 'DATE', r: 'Parseo YYYY-MM-DD' },
    { o: 'OBSERVACIONES', n: 'observacion', t: 'TEXT', r: 'Sanitizado HTML' },
  ];

  const items = matrix && matrix.length > 0 ? matrix : defaultEntries;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '600', margin: 0, color: 'var(--color-ink-black)' }}>
          Matriz de Normalización de Cabeceras
        </h3>
        <span style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#2563eb', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
          Esquema Homologado
        </span>
      </div>

      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cabecera Original Cruda</th>
              <th>Cabecera Canónica Normalizada</th>
              <th>Tipo de Dato</th>
              <th>Estado de Mapeo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                  {row.o || row.cabecera_original}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--color-sienna-brown)', fontSize: '13px' }}>
                  {row.n || row.cabecera_normalizada}
                </td>
                <td>
                  <span style={{
                    backgroundColor: 'var(--color-mist-gray)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    color: 'var(--color-ink-black)',
                    fontWeight: 600
                  }}>
                    {row.t || row.tipo_dato}
                  </span>
                </td>
                <td>
                  <span className="badge-status badge-status-completed" style={{ fontSize: '11px' }}>
                    ✔ {row.r || row.regla || 'Mapeado'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
