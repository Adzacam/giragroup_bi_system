import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileSpreadsheet, FileText, Database, CheckCircle, AlertCircle, RefreshCw, Eye, AlertTriangle, Play, Trash2 } from 'lucide-react';
import ResponsiveTable from '../../../components/shared/ResponsiveTable';
import { sileoToast } from '../../../services/sileoToast';
import { getSourceTableMeta } from '../../../utils/sourceLabelUtils';

export default function SourcesTable({
  sources = [],
  selectedIds = [],
  onToggleSelect,
  onSelectAll,
  onClearSelection,
  onProcessSelected,
  onReprocess,
  onSelectDetail,
  onDeleteSource,
  onDeleteSelected,
  isReprocessingId,
  title,
  mode = 'all', // 'queue' | 'history' | 'all'
  emptyMessage,
}) {
  const navigate = useNavigate();
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
          <AlertCircle size={13} /> En proceso
        </span>
      );
    }
    if (status === 'ready' || status === 'pending') {
      return (
        <span className="badge-status" style={{ backgroundColor: 'rgba(217, 155, 38, 0.15)', color: '#b45309', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <AlertCircle size={13} /> Listo para Procesar
        </span>
      );
    }
    return (
      <span className="badge-status" style={{ backgroundColor: 'rgba(217, 56, 58, 0.12)', color: 'var(--color-alert-red)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
        <AlertTriangle size={13} /> Error de formato
      </span>
    );
  };

  const isAllSelected = sources.length > 0 && sources.every((item) => selectedIds.some((sId) => String(sId) === String(item.id)));

  const handleProcessSelectedClick = () => {
    if (selectedIds.length === 0) {
      sileoToast.warning({
        title: 'Selección Requerida',
        description: 'Debe marcar al menos un archivo de la tabla para continuar.'
      });
      return;
    }
    if (onProcessSelected) {
      onProcessSelected(selectedIds);
    } else {
      navigate(`/dataops/ingesta?tab=pipeline&autoRun=true&docIds=${selectedIds.join(',')}`);
    }
  };

  const displayTitle = title || (
    mode === 'queue'
      ? 'Archivos en Cola para Análisis y Normalización'
      : mode === 'history'
      ? 'Historial de Archivos Ingeridos y Procesados'
      : 'Archivos Procesados Recientemente'
  );

  return (
    <div style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 className="serif-heading" style={{ fontSize: '19px', margin: 0, color: 'var(--color-ink-black)' }}>
            {displayTitle}
          </h3>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
            {mode === 'queue'
              ? `${sources.length} archivo(s) pendientes de normalización e inserción.`
              : `${sources.length} archivo(s) registrados en el catálogo documental.`}
          </div>
        </div>
      </div>

      {/* Barra de Acciones en Lote */}
      {selectedIds.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 18px',
            backgroundColor: 'var(--color-paper-white)',
            border: '1px solid var(--color-border)',
            borderLeft: '4px solid var(--color-gira-gold)',
            borderRadius: '12px',
            marginBottom: '16px',
            boxShadow: 'var(--shadow-subtle)',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--color-gira-gold)',
                color: '#0C1E33',
                fontWeight: 700,
                fontSize: '12px',
                width: '26px',
                height: '26px',
                borderRadius: '50%',
                boxShadow: '0 2px 6px rgba(217, 155, 38, 0.35)',
              }}
            >
              {selectedIds.length}
            </span>
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
              {selectedIds.length === 1
                ? '1 archivo seleccionado para procesar'
                : `${selectedIds.length} archivos seleccionados para procesar`}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              onClick={() => onDeleteSelected && onDeleteSelected(selectedIds)}
              className="btn-pill-ghost"
              style={{
                padding: '6px 14px',
                fontSize: '12.5px',
                color: 'var(--color-alert-red)',
                backgroundColor: 'rgba(217, 56, 58, 0.08)',
                border: '1px solid rgba(217, 56, 58, 0.25)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
              title="Eliminar permanentemente los archivos seleccionados"
            >
              <Trash2 size={13} />
              Eliminar Seleccionados ({selectedIds.length})
            </button>

            <button
              type="button"
              onClick={() => (onClearSelection ? onClearSelection() : onSelectAll && onSelectAll(false))}
              className="btn-pill-ghost"
              style={{
                padding: '6px 14px',
                fontSize: '12.5px',
                color: 'var(--color-slate-gray)',
                backgroundColor: 'var(--color-mist-gray)',
                border: '1px solid var(--color-border)',
              }}
            >
              Deseleccionar
            </button>

            <button
              type="button"
              onClick={handleProcessSelectedClick}
              className="btn-pill-dark"
              style={{
                padding: '7px 20px',
                fontSize: '13px',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                backgroundColor: 'var(--color-ink-black)',
                color: 'var(--color-paper-white)',
                borderRadius: '9999px',
              }}
            >
              {mode === 'history' ? (
                <>
                  <RefreshCw size={12} />
                  <span>Volver a Procesar Seleccionados ({selectedIds.length}) →</span>
                </>
              ) : (
                <>
                  <Play size={12} fill="currentColor" />
                  <span>Convertir a Texto Plano ({selectedIds.length}) →</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th style={{ width: '42px', textAlign: 'center' }}>
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  ref={(el) => {
                    if (el) {
                      el.indeterminate = selectedIds.length > 0 && selectedIds.length < sources.length;
                    }
                  }}
                  onChange={(e) => onSelectAll && onSelectAll(e.target.checked)}
                  aria-label="Seleccionar o deseleccionar todos los archivos"
                  style={{
                    accentColor: 'var(--color-sienna-brown)',
                    width: '16px',
                    height: '16px',
                    cursor: 'pointer',
                  }}
                />
              </th>
              <th>Entidad & Tabla Canónica</th>
              <th>Tipo & Esquema</th>
              <th>Registros Detectados</th>
              <th>Fecha y Hora</th>
              <th>Estado</th>
              <th style={{ textAlign: 'right' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {sources.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--color-slate-gray)' }}>
                  <div style={{ fontSize: '13px', fontWeight: 500 }}>
                    {emptyMessage || (mode === 'queue' ? 'No hay archivos en cola pendientes de procesamiento.' : 'No hay archivos en el historial de procesados.')}
                  </div>
                </td>
              </tr>
            ) : (
              sources.map((item) => {
              const isReprocessing = isReprocessingId === item.id;
              const isSelected = selectedIds.some((sId) => String(sId) === String(item.id));
              const meta = getSourceTableMeta(item.name, item.type);

              return (
                <tr
                  key={item.id}
                  onClick={(e) => {
                    if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT' && !e.target.closest('button')) {
                      onToggleSelect && onToggleSelect(item.id);
                    }
                  }}
                  style={{
                    backgroundColor: isSelected ? 'rgba(217, 155, 38, 0.08)' : undefined,
                    transition: 'background-color 0.15s ease',
                    cursor: 'pointer',
                  }}
                >
                  <td style={{ textAlign: 'center', width: '42px' }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        e.stopPropagation();
                        onToggleSelect && onToggleSelect(item.id);
                      }}
                      aria-label={`Seleccionar ${item.name}`}
                      style={{
                        accentColor: 'var(--color-sienna-brown)',
                        width: '16px',
                        height: '16px',
                        cursor: 'pointer',
                      }}
                    />
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                      <div style={{ marginTop: '2px' }}>{getSourceIcon(item.type)}</div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--color-ink-black)' }}>
                            {meta.domainTitle}
                          </span>
                          <span
                            style={{
                              fontSize: '11px',
                              fontFamily: 'var(--font-mono)',
                              fontWeight: 700,
                              padding: '1px 6px',
                              borderRadius: '4px',
                              color: meta.color,
                              backgroundColor: meta.bgColor,
                              border: `1px solid ${meta.borderColor}`,
                            }}
                          >
                            {meta.table}
                          </span>
                        </div>
                        <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{item.name}</span>
                          <span style={{ color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)', fontSize: '10.5px' }}>
                            sha256: {item.sha256 || '8f4e2a1b'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      <span 
                        className="badge-source" 
                        style={{ 
                          ...getSourceBadgeStyle(item.type),
                          borderRadius: '9999px',
                          padding: '3px 8px',
                          fontSize: '11px',
                          fontWeight: 600,
                          alignSelf: 'flex-start',
                        }}
                      >
                        {item.type}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 500 }}>
                        {meta.category} · <code style={{ fontSize: '10px', color: meta.color }}>{meta.tableType}</code>
                      </span>
                    </div>
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

                      {mode === 'history' ? (
                        <button
                          type="button"
                          onClick={() => onReprocess ? onReprocess(item.id) : navigate(`/dataops/ingesta?tab=pipeline&autoRun=true&docId=${item.id}`)}
                          disabled={isReprocessing}
                          style={{
                            background: 'var(--color-mist-gray)',
                            border: '1px solid var(--color-border)',
                            color: 'var(--color-ink-black)',
                            cursor: isReprocessing ? 'not-allowed' : 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11.5px',
                            fontWeight: 600,
                            padding: '4px 10px',
                            borderRadius: '9999px',
                            opacity: isReprocessing ? 0.5 : 1
                          }}
                          title="Volver a procesar en el pipeline"
                        >
                          <RefreshCw size={11} className={isReprocessing ? 'spin' : ''} />
                          {isReprocessing ? 'Reprocesando...' : 'Volver a procesar'}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => navigate(`/dataops/ingesta?tab=pipeline&autoRun=true&docId=${item.id}`)}
                          style={{
                            backgroundColor: 'var(--color-ink-black)',
                            border: 'none',
                            color: '#ffffff',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontSize: '12px',
                            fontWeight: 600,
                            padding: '4px 12px',
                            borderRadius: '9999px',
                            transition: 'opacity 0.15s ease',
                            whiteSpace: 'nowrap'
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                          onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                          title="Convertir inmediatamente a texto plano y procesar"
                        >
                          <Play size={11} fill="currentColor" /> Convertir a Texto Plano
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onDeleteSource && onDeleteSource(item.id, item.name)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-slate-gray)',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '28px',
                          height: '28px',
                          borderRadius: '50%',
                          transition: 'all 0.15s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.color = 'var(--color-alert-red)';
                          e.currentTarget.style.backgroundColor = 'rgba(217, 56, 58, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.color = 'var(--color-slate-gray)';
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                        title={`Eliminar '${item.name}'`}
                        aria-label={`Eliminar '${item.name}'`}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            }))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
