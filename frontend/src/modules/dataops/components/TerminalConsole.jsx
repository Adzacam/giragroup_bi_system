import React, { useEffect, useRef } from 'react';
import { Terminal, Trash2 } from 'lucide-react';

export default function TerminalConsole({ logs, onClear, isStreaming }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const getNivelColor = (type) => {
    switch (type) {
      case 'INFO':
        return '#60a5fa'; // Blue
      case 'WARN':
        return '#f59e0b'; // Amber
      case 'SUCCESS':
        return '#34d399'; // Emerald green
      case 'ERROR':
        return '#f87171'; // Red
      default:
        return '#94a3b8';
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: '600', margin: 0, color: 'var(--color-ink-black)' }}>
          <Terminal size={16} /> Consola de Ejecución en Tiempo Real (pipeline.py)
        </h3>
        <button 
          onClick={onClear} 
          type="button"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-slate-gray)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '12px',
            padding: '4px 8px',
            borderRadius: '6px'
          }}
          title="Limpiar registros de consola"
        >
          <Trash2 size={13} /> Limpiar Consola
        </button>
      </div>

      <div 
        ref={terminalRef}
        className="terminal-container" 
        style={{ 
          backgroundColor: '#0f1113', 
          borderRadius: '16px', 
          padding: '18px 20px', 
          fontFamily: 'var(--font-mono)', 
          fontSize: '12.5px', 
          height: '320px', 
          overflowY: 'auto', 
          color: '#e2e8f0',
          border: '1px solid #1e293b',
          boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.5)',
          scrollbarWidth: 'thin'
        }}
      >
        {(!logs || logs.length === 0) ? (
          <div style={{ color: '#64748b', fontStyle: 'normal', padding: '36px 0', textAlign: 'center' }}>
            Consola en espera. Presione "Simular Nuevo Procesamiento" para ejecutar el pipeline.
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} style={{ marginBottom: '8px', display: 'flex', gap: '10px', lineHeight: 1.45, flexWrap: 'wrap' }}>
              <span style={{ color: '#64748b' }}>[{log.time || '10:15:00'}]</span>
              <span style={{ 
                color: getNivelColor(log.type || log.nivel),
                minWidth: '56px',
                fontWeight: 600
              }}>
                [{log.type || log.nivel || 'INFO'}]
              </span>
              <span style={{ color: '#c084fc', minWidth: '95px' }}>{log.module || log.modulo || 'pipeline.py'}:</span>
              <span style={{ color: (log.type === 'SUCCESS' || log.nivel === 'SUCCESS') ? '#86efac' : '#f1f5f9' }}>
                {log.msg || log.mensaje}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
