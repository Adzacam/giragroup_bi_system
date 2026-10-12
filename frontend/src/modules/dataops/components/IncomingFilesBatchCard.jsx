import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet, FileText, FileCode, CheckCircle2, Clock,
  Activity, Play, FileUp, Trash2, CheckSquare, Square
} from 'lucide-react';

export default function IncomingFilesBatchCard({
  files = [],
  isProcessing = false,
  pipelineFinished = false,
  onProcessSingle,
  onProcessBatch,
  onDeleteSingle,
  onDeleteBatch,
  onNavigateToUpload,
}) {
  const [selectedIds, setSelectedIds] = useState([]);

  // Sincronizar selección si cambian los archivos disponibles
  useEffect(() => {
    const validFileIds = new Set(files.map((f) => f.id));
    setSelectedIds((prev) => prev.filter((id) => validFileIds.has(id)));
  }, [files]);

  const allSelected = files.length > 0 && selectedIds.length === files.length;
  const isIndeterminate = selectedIds.length > 0 && selectedIds.length < files.length;

  const handleToggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(files.map((f) => f.id));
    }
  };

  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleProcessSelected = () => {
    if (selectedIds.length === 0) return;
    if (onProcessBatch) {
      onProcessBatch(selectedIds);
    } else if (onProcessSingle) {
      onProcessSingle(selectedIds[0]);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    if (onDeleteBatch) {
      onDeleteBatch(selectedIds);
      setSelectedIds([]);
    }
  };

  const getFileIcon = (fileName, format) => {
    const fn = (fileName || '').toLowerCase();
    const fmt = (format || '').toLowerCase();
    if (fn.endsWith('.csv') || fmt.includes('forms')) {
      return <FileText size={18} color="#0284c7" />;
    }
    if (fn.endsWith('.xml') || fmt.includes('moodle')) {
      return <FileCode size={18} color="#9333ea" />;
    }
    if (fmt.includes('cobranza') || fmt.includes('sheets')) {
      return <FileSpreadsheet size={18} color="var(--color-sienna-brown)" />;
    }
    return <FileSpreadsheet size={18} color="var(--color-alert-green)" />;
  };

  return (
    <div
      className="floating-artifact"
      style={{
        padding: '20px 24px',
        borderRadius: 'var(--radius-cards)',
        border: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-paper-white)',
        marginBottom: '24px',
        boxShadow: 'var(--shadow-subtle)',
      }}
    >
      {/* Encabezado Superior */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
              color: 'var(--color-gira-gold, #D99B26)',
              fontWeight: 700,
            }}
          >
            Lote Documental Activo para Normalización & Conversión a Texto Plano
          </div>
          <div
            style={{
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--color-ink-black)',
              marginTop: '2px',
            }}
          >
            {files.length} fuente(s) en cola de ejecución del pipeline
            {selectedIds.length > 0 && (
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 500,
                  color: 'var(--color-slate-gray)',
                  marginLeft: '8px',
                }}
              >
                ({selectedIds.length} seleccionada{selectedIds.length > 1 ? 's' : ''})
              </span>
            )}
          </div>
        </div>

        {/* Estado del Pipeline */}
        <div>
          {isProcessing ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-gira-gold)',
                backgroundColor: 'rgba(217, 155, 38, 0.12)',
                padding: '5px 14px',
                borderRadius: '9999px',
              }}
            >
              <Activity size={13} className="spin" /> Pipeline en Ejecución Activa
            </span>
          ) : pipelineFinished ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-alert-green)',
                backgroundColor: 'rgba(34, 197, 94, 0.12)',
                padding: '5px 14px',
                borderRadius: '9999px',
              }}
            >
              <CheckCircle2 size={13} /> {files.length} Archivos Normalizados y Confirmados
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-slate-gray)',
                backgroundColor: 'var(--color-mist-gray)',
                padding: '5px 14px',
                borderRadius: '9999px',
              }}
            >
              <Clock size={13} /> {files.length > 0 ? 'Preparado para Iniciar' : 'Cola Vacía'}
            </span>
          )}
        </div>
      </div>

      {/* Barra de Acciones y Selección en Lote (cuando hay archivos) */}
      {files.length > 0 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '10px 14px',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '12px',
            marginBottom: '14px',
            border: '1px solid var(--color-border)',
            flexWrap: 'wrap',
            gap: '10px',
          }}
        >
          {/* Checkbox Seleccionar Todos */}
          <label
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12.5px',
              fontWeight: 600,
              color: 'var(--color-ink-black)',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              userSelect: 'none',
            }}
          >
            <input
              type="checkbox"
              checked={allSelected}
              ref={(input) => {
                if (input) input.indeterminate = isIndeterminate;
              }}
              onChange={handleToggleSelectAll}
              disabled={isProcessing}
              style={{
                accentColor: 'var(--color-ink-black)',
                width: '16px',
                height: '16px',
                cursor: 'pointer',
              }}
            />
            <span>
              {allSelected
                ? 'Deseleccionar todos'
                : `Seleccionar todos (${files.length})`}
            </span>
          </label>

          {/* Botones de acción en lote */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn-pill-dark"
              onClick={handleProcessSelected}
              disabled={isProcessing || selectedIds.length === 0}
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                opacity: selectedIds.length === 0 || isProcessing ? 0.45 : 1,
                cursor: selectedIds.length === 0 || isProcessing ? 'not-allowed' : 'pointer',
              }}
              title={
                selectedIds.length === 0
                  ? 'Seleccione uno o más archivos para procesar'
                  : `Procesar ${selectedIds.length} archivo(s)`
              }
            >
              <Play size={12} fill="currentColor" />
              <span>
                Procesar Seleccionados ({selectedIds.length})
              </span>
            </button>

            <button
              type="button"
              onClick={handleDeleteSelected}
              disabled={isProcessing || selectedIds.length === 0}
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                borderRadius: '9999px',
                border: '1px solid rgba(217, 56, 58, 0.35)',
                color: '#d9383a',
                backgroundColor: 'rgba(217, 56, 58, 0.06)',
                fontWeight: 600,
                opacity: selectedIds.length === 0 || isProcessing ? 0.45 : 1,
                cursor: selectedIds.length === 0 || isProcessing ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
              }}
              title={
                selectedIds.length === 0
                  ? 'Seleccione archivos para eliminar'
                  : `Eliminar ${selectedIds.length} archivo(s)`
              }
            >
              <Trash2 size={12} />
              <span>Eliminar ({selectedIds.length})</span>
            </button>
          </div>
        </div>
      )}

      {/* Rejilla de archivos o estado vacío */}
      {files.length === 0 ? (
        <div
          style={{
            padding: '36px 20px',
            textAlign: 'center',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '12px',
            border: '1px dashed var(--color-border)',
          }}
        >
          <p
            style={{
              color: 'var(--color-slate-gray)',
              fontSize: '14px',
              margin: '0 0 16px 0',
            }}
          >
            No hay fuentes documentales en la cola de procesamiento activa.
          </p>
          <button
            type="button"
            className="btn-pill-dark"
            onClick={onNavigateToUpload}
            style={{
              padding: '8px 20px',
              fontSize: '13px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <FileUp size={15} />
            <span>+ Ir a Cargar Fuentes Documentales</span>
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '12px',
            maxHeight: '280px',
            overflowY: 'auto',
            paddingRight: '4px',
          }}
        >
          {files.map((file, idx) => {
            const isItemProcessing = isProcessing;
            const isItemCompleted = pipelineFinished || file.status === 'completed';
            const isSelected = selectedIds.includes(file.id);

            return (
              <div
                key={file.id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: isSelected
                    ? 'rgba(217, 155, 38, 0.05)'
                    : 'var(--color-fog-white)',
                  border: isSelected
                    ? '1px solid var(--color-gira-gold, #D99B26)'
                    : isItemProcessing
                    ? '1px solid var(--color-gira-gold)'
                    : isItemCompleted
                    ? '1px solid rgba(34, 197, 94, 0.3)'
                    : '1px solid var(--color-border)',
                  borderRadius: '12px',
                  gap: '10px',
                  transition: 'all 0.15s ease',
                }}
              >
                {/* Checkbox individual */}
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleToggleSelect(file.id)}
                  disabled={isProcessing}
                  style={{
                    accentColor: 'var(--color-ink-black)',
                    width: '16px',
                    height: '16px',
                    cursor: isProcessing ? 'not-allowed' : 'pointer',
                    flexShrink: 0,
                  }}
                />

                {/* Info Archivo */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    minWidth: 0,
                    flex: 1,
                  }}
                >
                  <div style={{ flexShrink: 0 }}>
                    {getFileIcon(file.name, file.format || file.type)}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      style={{
                        fontSize: '12.5px',
                        fontWeight: 600,
                        color: 'var(--color-ink-black)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                      title={file.name}
                    >
                      {file.name}
                    </div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-slate-gray)',
                        marginTop: '2px',
                      }}
                    >
                      {file.format || file.type || 'Excel Acta'} ·{' '}
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        {file.size || `${(file.records || 0).toLocaleString()} reg`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Acciones del Archivo */}
                <div
                  style={{
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  {isItemProcessing ? (
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 600,
                        color: 'var(--color-gira-gold)',
                        backgroundColor: 'rgba(217, 155, 38, 0.12)',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <Activity size={10} className="spin" /> Normalizando
                    </span>
                  ) : isItemCompleted ? (
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 600,
                        color: 'var(--color-alert-green)',
                        backgroundColor: 'rgba(34, 197, 94, 0.12)',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <CheckCircle2 size={10} /> Homologado
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onProcessSingle && onProcessSingle(file.id)}
                      style={{
                        background: 'none',
                        border: '1px solid var(--color-border)',
                        color: 'var(--color-ink-black)',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        backgroundColor: 'var(--color-paper-white)',
                      }}
                      title="Procesar este archivo individual"
                    >
                      <Play size={10} fill="currentColor" /> Procesar
                    </button>
                  )}

                  {/* Botón eliminar archivo individual */}
                  {!isProcessing && (
                    <button
                      type="button"
                      onClick={() => onDeleteSingle && onDeleteSingle(file.id, file.name)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#d9383a',
                        padding: '4px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 0.75,
                        transition: 'opacity 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                      onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.75')}
                      title={`Eliminar ${file.name}`}
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
