import React, { useEffect, useRef } from 'react';
import { Terminal, Activity, Trash2, X, RefreshCw } from 'lucide-react';

export default function PipelineTelemetryDrawer({
  isOpen,
  onClose,
  logs = [],
  onClearLogs,
  isProcessing = false,
  lotName = 'Lote: POS-2026-B_M3'
}) {
  const scrollContainerRef = useRef(null);

  // Auto-scroll to bottom whenever new logs arrive or drawer opens
  useEffect(() => {
    if (isOpen && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  // Map log level to designated HUD color
  const getNivelColor = (level) => {
    const lvl = (level || 'INFO').toUpperCase();
    switch (lvl) {
      case 'INFO':
        return '#60a5fa'; // Blue
      case 'WARN':
      case 'WARNING':
        return '#f59e0b'; // Amber
      case 'SUCCESS':
        return '#34d399'; // Emerald
      case 'ERROR':
        return '#f87171'; // Red
      default:
        return '#94a3b8'; // Slate
    }
  };

  // Map log level to border-left accent color
  const getBorderColor = (level) => {
    const lvl = (level || 'INFO').toUpperCase();
    switch (lvl) {
      case 'INFO':
        return '#3b82f6';
      case 'WARN':
      case 'WARNING':
        return '#f59e0b';
      case 'SUCCESS':
        return '#10b981';
      case 'ERROR':
        return '#ef4444';
      default:
        return '#374151';
    }
  };

  // Helper to normalize log entry whether it's an object or plain string
  const formatLogItem = (log, index) => {
    if (typeof log === 'string') {
      return {
        id: index,
        time: new Date().toLocaleTimeString('en-US', { hour12: false }),
        level: 'INFO',
        module: 'pipeline.py',
        message: log
      };
    }
    return {
      id: index,
      time: log.time || log.timestamp || new Date().toLocaleTimeString('en-US', { hour12: false }),
      level: (log.type || log.nivel || 'INFO').toUpperCase(),
      module: log.module || log.modulo || 'pipeline.py',
      message: log.msg || log.mensaje || ''
    };
  };

  return (
    <>
      {/* ── Backdrop con desenfoque y opacidad ── */}
      {isOpen && (
        <div
          role="presentation"
          aria-hidden="true"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.55)',
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            zIndex: 999,
            transition: 'opacity 0.25s ease'
          }}
          onClick={onClose}
        />
      )}

      {/* ── Drawer lateral deslizante (540px) ── */}
      <aside
        className="pipeline-telemetry-drawer"
        aria-label="Panel de Telemetría de Pipeline"
        aria-hidden={!isOpen}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '540px',
          maxWidth: '100vw',
          backgroundColor: '#0f1113',
          zIndex: 1000,
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '-10px 0 35px rgba(0, 0, 0, 0.65)',
          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
          color: '#e2e8f0',
          borderLeft: '1px solid #1e293b',
          boxSizing: 'border-box'
        }}
      >
        {/* ── Encabezado HUD ── */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            borderBottom: '1px solid #2d3748',
            paddingBottom: '16px'
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: '13.5px',
                fontWeight: '600',
                color: '#a0aec0',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                letterSpacing: '0.4px'
              }}
            >
              <Terminal size={16} color="#63b3ed" />
              <span>PIPELINE TELEMETRY · PIPELINE.PY v2.0</span>
            </h3>
            {lotName && (
              <div
                style={{
                  fontSize: '11px',
                  color: '#64748b',
                  marginTop: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span>Target:</span>
                <span
                  style={{
                    color: '#94a3b8',
                    backgroundColor: '#1e293b',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: '500'
                  }}
                >
                  {lotName}
                </span>
                {isProcessing && (
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: '#38bdf8',
                      fontSize: '10.5px'
                    }}
                  >
                    <RefreshCw size={11} className="spin-animation" style={{ animation: 'spin 1s linear infinite' }} />
                    Streaming...
                  </span>
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {onClearLogs && (
              <button
                type="button"
                onClick={onClearLogs}
                title="Limpiar Consola"
                style={{
                  background: 'none',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  borderRadius: '6px',
                  padding: '6px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '11px',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#f87171';
                  e.currentTarget.style.borderColor = '#ef4444';
                  e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.borderColor = '#334155';
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <Trash2 size={14} />
                <span>Limpiar</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              title="Cerrar Consola"
              aria-label="Cerrar panel de telemetría"
              style={{
                background: 'none',
                border: 'none',
                color: '#a0aec0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4px',
                borderRadius: '6px',
                transition: 'color 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#a0aec0')}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* ── Lista de logs y pasos en tiempo real ── */}
        <div
          ref={scrollContainerRef}
          className="pipeline-telemetry-body"
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingRight: '6px',
            scrollbarWidth: 'thin',
            scrollbarColor: '#334155 transparent'
          }}
        >
          {(!logs || logs.length === 0) ? (
            <div
              style={{
                color: '#64748b',
                fontStyle: 'italic',
                padding: '48px 16px',
                textAlign: 'center',
                fontSize: '12.5px',
                lineHeight: '1.6',
                border: '1px dashed #2d3748',
                borderRadius: '8px'
              }}
            >
              Consola en espera de telemetría.
              <br />
              Ejecute o simule el procesamiento del pipeline para transmitir registros en vivo.
            </div>
          ) : (
            logs.map((rawLog, index) => {
              const log = formatLogItem(rawLog, index);
              const nivelColor = getNivelColor(log.level);
              const borderColor = getBorderColor(log.level);

              return (
                <div
                  key={log.id}
                  className="telemetry-step"
                  style={{
                    marginBottom: '14px',
                    borderLeft: `2px solid ${borderColor}`,
                    paddingLeft: '12px',
                    paddingTop: '3px',
                    paddingBottom: '3px',
                    fontSize: '12.5px',
                    lineHeight: '1.55',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '0 4px 4px 0',
                    animation: 'fadeInUp 0.25s ease-out forwards',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '3px'
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      flexWrap: 'wrap'
                    }}
                  >
                    {/* Timestamp */}
                    <span style={{ color: '#64748b', fontSize: '11px', letterSpacing: '0.2px' }}>
                      [{log.time}]
                    </span>

                    {/* Nivel con badge color */}
                    <span
                      style={{
                        color: nivelColor,
                        fontWeight: '700',
                        fontSize: '11px',
                        letterSpacing: '0.4px'
                      }}
                    >
                      [{log.level}]
                    </span>

                    {/* Módulo en violeta claro */}
                    <span
                      style={{
                        color: '#c084fc',
                        fontWeight: '600',
                        fontSize: '11.5px'
                      }}
                    >
                      {log.module.endsWith(':') ? log.module : `${log.module}:`}
                    </span>
                  </div>

                  {/* Mensaje del paso */}
                  <div
                    style={{
                      color:
                        log.level === 'SUCCESS'
                          ? '#86efac'
                          : log.level === 'ERROR'
                          ? '#fc8181'
                          : log.level === 'WARN'
                          ? '#fde68a'
                          : '#e2e8f0',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontSize: '12.5px'
                    }}
                  >
                    {log.message}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ── Keyframes inline ── */}
        <style>
          {`
            @keyframes fadeInUp {
              from {
                opacity: 0;
                transform: translateY(8px);
              }
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}
        </style>

        {/* ── Pie técnico del Drawer ── */}
        <footer
          style={{
            marginTop: 'auto',
            paddingTop: '16px',
            borderTop: '1px solid #2d3748',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '10px',
            fontSize: '11.5px',
            color: '#718096'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Status:</span>
            <span
              style={{
                color: isProcessing ? '#38bdf8' : '#48bb78',
                fontWeight: '600',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: isProcessing ? '#38bdf8' : '#48bb78',
                  boxShadow: `0 0 6px ${isProcessing ? '#38bdf8' : '#48bb78'}`
                }}
              />
              {isProcessing ? 'STREAMING / ACTIVE' : 'CONNECTED'}
            </span>
          </div>

          <div>
            <span>PostgreSQL Hook: </span>
            <span style={{ color: '#48bb78', fontWeight: '600' }}>VALID</span>
          </div>

          <div>
            <span>Staging: </span>
            <span style={{ color: '#38bdf8', fontWeight: '600' }}>CONFIRMED / SYNCHRONIZED</span>
          </div>
        </footer>
      </aside>
    </>
  );
}
