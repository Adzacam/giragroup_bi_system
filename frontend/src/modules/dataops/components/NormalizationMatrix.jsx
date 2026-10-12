import React from 'react';
import ResponsiveTable from '../../../components/shared/ResponsiveTable';

export default function NormalizationMatrix({ matrix }) {
  const defaultEntries = [
    { o: 'NOMBRES Y APELLIDOS', n: 'nombre_completo', rol: 'ROL_ESTUDIANTE_NOMBRE', t: 'VARCHAR', r: 'Mapeo directo', catalogo: 'Identificador Persona' },
    { o: 'CALIF_FINAL', n: 'nota_final', rol: 'ROL_CALIFICACION', t: 'NUMERIC', r: 'Conversión a float', catalogo: 'Medida Rendimiento [0-100]' },
    { o: 'DOC_IDENTIDAD/CI', n: 'ci_estudiante', rol: 'ROL_ESTUDIANTE_CI', t: 'VARCHAR', r: 'Limpieza alfanumérica', catalogo: 'Llave Primaria Candidata' },
    { o: 'COD_MODULO', n: 'codigo_modulo', rol: 'ROL_MODULO_CODIGO', t: 'VARCHAR', r: 'Mapeo directo', catalogo: 'cat_modulo (3NF)' },
    { o: 'FECHA_EVAL', n: 'fecha_asentamiento', rol: 'ROL_FECHA_REGISTRO', t: 'DATE', r: 'Parseo YYYY-MM-DD', catalogo: 'dim_tiempo' },
    { o: 'DOCENTE / PROFESOR', n: 'nombre_docente', rol: 'ROL_DOCENTE_NOMBRE', t: 'VARCHAR', r: 'Limpieza textual', catalogo: 'cat_docente (3NF)' },
    { o: 'CONCEPTO / ITEM', n: 'concepto_financiero', rol: 'ROL_CONCEPTO_FIN', t: 'VARCHAR', r: 'Homologación categoría', catalogo: 'cat_concepto_financiero (3NF)' },
    { o: 'MONTO_BS', n: 'monto_cuota', rol: 'ROL_MONTO_MONEDA', t: 'NUMERIC', r: 'Moneda Bs.', catalogo: 'Métrica Financiera (Bs.)' },
    { o: 'OBSERVACIONES', n: 'observacion', rol: 'ROL_METADATO_TEXTO', t: 'TEXT', r: 'Sanitizado HTML', catalogo: 'Auditoría Staging' },
  ];

  const items = matrix && matrix.length > 0 ? matrix : defaultEntries;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: '600', margin: 0, color: 'var(--color-ink-black)' }}>
            Matriz de Normalización de Cabeceras & Roles Semánticos
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
            Clasificación a nivel de cabecera documental contra catálogos 3NF (cursos, docentes, conceptos financieros). No concatena texto plano por celda.
          </p>
        </div>
        <span style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#2563eb', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
          Esquema Homologado
        </span>
      </div>

      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cabecera Original Cruda</th>
              <th>Cabecera Canónica</th>
              <th>Rol Semántico (Catálogo / Rol)</th>
              <th>Tipo de Dato</th>
              <th>Destino / Catálogo 3NF</th>
              <th>Estado</th>
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
                    backgroundColor: 'rgba(217, 155, 38, 0.12)',
                    color: '#b45309',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    fontWeight: 700
                  }}>
                    {row.rol || (
                      (row.n || row.cabecera_normalizada || '').includes('estudiante') ? 'ROL_ESTUDIANTE' :
                      (row.n || row.cabecera_normalizada || '').includes('modulo') ? 'ROL_MODULO' :
                      (row.n || row.cabecera_normalizada || '').includes('docente') ? 'ROL_DOCENTE' :
                      (row.n || row.cabecera_normalizada || '').includes('nota') ? 'ROL_CALIFICACION' :
                      (row.n || row.cabecera_normalizada || '').includes('monto') ? 'ROL_MONTO_MONEDA' :
                      'ROL_CANONICO'
                    )}
                  </span>
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
                <td style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: 500 }}>
                  {row.catalogo || (
                    (row.n || row.cabecera_normalizada || '').includes('modulo') ? 'cat_modulo (3NF)' :
                    (row.n || row.cabecera_normalizada || '').includes('docente') ? 'cat_docente (3NF)' :
                    (row.n || row.cabecera_normalizada || '').includes('concepto') ? 'cat_concepto_financiero (3NF)' :
                    (row.n || row.cabecera_normalizada || '').includes('fecha') ? 'dim_tiempo' :
                    'staging_registros_crudos'
                  )}
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
