import React from 'react';
import { FileSpreadsheet, FileText, Database, CheckCircle, AlertCircle, RefreshCw, Eye, AlertTriangle } from 'lucide-react';
import ResponsiveTable from '../../../components/shared/ResponsiveTable';

export default function SourcesTable({ sources, onReprocess, onSelectDetail, isReprocessingId }) {
  const getSourceIcon = (type) => {
    const t = (type || '').toLowerCase();
    if (t.includes('excel') || t.includes('acta')) return <FileSpreadsheet size={18} color="#3b82f6" />;
    if (t.includes('forms') || t.includes('csv')) return <FileText size={18} color="#8b5cf6" />;
    if (t.includes('moodle')) return <Database size={18} color="#f97316" />;
    return <FileSpreadsheet size={18} color="var(--color-sienna-brown)" />;
  };

  const getSourceBadgeStyle = (type) => {
    const t = (type || '').toLowerCase();
    if (t.includes('forms')) return { backgroundColor: 'rgba(139, 92, 246, 0.12)', color: '#8b5cf6' };
    if (t.includes('moodle')) return { backgroundColor: 'rgba(249, 115, 22, 0.12)', color: '#ea580c' };
    if (t.includes('cartera') || t.includes('sheets')) return { backgroundColor: 'rgba(180, 83, 9, 0.12)', color: '#b45309' };
    return { backgroundColor: 'rgba(59, 130, 246, 0.12)', color: '#2563eb' };
  };

  const getStatusBadge = (status) => {
    if (status === 'completed') {
      return (
        <span className="badge-status badge-status-completed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <CheckCircle size={13} /> Completado
        </span>
      );
    }
    if (status === 'warning' || status === 'processing') {
      return (
        <span className="badge-status badge-status-processing" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <AlertCircle size={13} /> En proceso (2)
        </span>
      );
    }
    return (
      <span className="badge-status" style={{ backgroundColor: 'rgba(217, 56, 58, 0.12)', color: 'var(--color-alert-red)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
        <AlertTriangle size={13} /> Error de formato
      </span>
    );
  };

  return (
    <div style={{ marginTop: '32px' }}>
      <h3 className="serif-heading" style={{ fontSize: '20px', marginBottom: '16px', color: 'var(--color-ink-black)' }}>
        Archivos Procesados Recientemente
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Nombre del Archivo</th>
              <th>Tipo de Fuente</th>
              <th>Registros Detectados</th>
              <th>Fecha y Hora</th>
              <th>Estado</th>
              <th style={{ textAlign: 'right' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((item) => {
              const isReprocessing = isReprocessingId === item.id;

              return (
                <tr key={item.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {getSourceIcon(item.type)}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--color-ink-black)' }}>
                          {item.name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>
                          sha256: {item.sha256 || '8f4e2a1b'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span 
                      className="badge-source" 
                      style={{ 
                        ...getSourceBadgeStyle(item.type),
                        borderRadius: '9999px',
                        padding: '4px 10px',
                        fontSize: '11.5px',
                        fontWeight: 600 
                      }}
                    >
                      {item.type}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                    {item.records.toLocaleString()}
                  </td>
                  <td style={{ color: 'var(--color-slate-gray)', fontSize: '13px' }}>
                    {item.date}
                  </td>
                  <td>
                    {getStatusBadge(item.status)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => onSelectDetail && onSelectDetail(item)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-slate-gray)',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '12.5px',
                          padding: '4px 8px',
                          borderRadius: '6px'
                        }}
                        title="Ver detalle de auditoría"
                      >
                        <Eye size={14} /> Detalle
                      </button>

                      <button
                        type="button"
                        onClick={() => onReprocess && onReprocess(item.id)}
                        disabled={isReprocessing}
                        style={{
                          background: 'none',
                          border: '1px solid var(--color-border)',
                          color: 'var(--color-ink-black)',
                          cursor: isReprocessing ? 'not-allowed' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '12px',
                          padding: '4px 10px',
                          borderRadius: '9999px',
                          backgroundColor: 'var(--color-paper-white)',
                          opacity: isReprocessing ? 0.5 : 1
                        }}
                        title="Reprocesar en el pipeline"
                      >
                        <RefreshCw size={12} className={isReprocessing ? 'spin' : ''} />
                        {isReprocessing ? 'Reprocesando...' : 'Reprocesar'}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
