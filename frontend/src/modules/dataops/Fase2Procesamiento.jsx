import React, { useState, useEffect, useRef } from 'react';
import { Play, FileUp, Split, Wand2, TableProperties, ShieldCheck, Database, Terminal, Trash2, CheckCircle2 } from 'lucide-react';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';

const INITIAL_LOGS = [
  { time: '10:15:02', type: 'INFO', module: 'dispatcher.py', msg: 'Iniciando pipeline para lote POS-2026-B_M3' },
  { time: '10:15:03', type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 completado (342 filas)' },
  { time: '10:15:04', type: 'INFO', module: 'cleaner.py', msg: 'Sanitizado de caracteres especiales finalizado' },
  { time: '10:15:05', type: 'INFO', module: 'mapper.py', msg: 'Mapeo de 12 columnas a esquema canónico' },
  { time: '10:15:06', type: 'WARN', module: 'validator.py', msg: '52 registros con inconsistencias estructurales detectados' },
  { time: '10:15:07', type: 'SUCCESS', module: 'pipeline.py', msg: '1,196 registros listos para staging' },
  { time: '10:15:08', type: 'INFO', module: 'loader.py', msg: 'Batch INSERT a esquema staging completado' },
  { time: '10:15:09', type: 'SUCCESS', module: 'pipeline.py', msg: 'Pipeline ejecutado con éxito en 4.2s' }
];

const STEPS = [
  { id: 1, name: 'Archivo Origen', time: '45ms', desc: 'Parseo UTF-8', icon: FileUp },
  { id: 2, name: 'Dispatcher', time: '110ms', desc: 'Acta_POS', icon: Split },
  { id: 3, name: 'Limpieza', time: '310ms', desc: 'Sanitizado', icon: Wand2 },
  { id: 4, name: 'Cabeceras', time: '140ms', desc: '12 Columnas', icon: TableProperties },
  { id: 5, name: 'Esquema', time: '195ms', desc: '95.8% Validez', icon: ShieldCheck },
  { id: 6, name: 'A Staging', time: '85ms', desc: 'INSERT batch', icon: Database },
];

export default function Fase2Procesamiento() {
  const [activeStep, setActiveStep] = useState(-1);
  const [logs, setLogs] = useState(INITIAL_LOGS);
  const { notify } = useNotifications();
  const terminalContainerRef = useRef(null);

  // Auto-scroll the terminal only during active simulation steps
  useEffect(() => {
    if (activeStep > 0 && terminalContainerRef.current) {
      terminalContainerRef.current.scrollTop = terminalContainerRef.current.scrollHeight;
    }
  }, [logs, activeStep]);

  const simulateProcessing = () => {
    setActiveStep(0);
    setLogs([]);
    const delays = [300, 800, 1500, 2200, 2900, 3600];
    const logMessages = [
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 en progreso...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'dispatcher.py', msg: 'Enrutando archivo Acta_POS...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'cleaner.py', msg: 'Limpieza y sanitizado de datos...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'mapper.py', msg: 'Normalizando cabeceras...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'WARN', module: 'validator.py', msg: 'Validación de esquema (95.8% validez)...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'SUCCESS', module: 'loader.py', msg: 'Inserción a Staging completada.' }
    ];

    delays.forEach((delay, index) => {
      setTimeout(() => {
        setActiveStep(index + 1);
        setLogs(prev => [...prev, logMessages[index]]);
      }, delay);
    });

    setTimeout(() => {
      setLogs(prev => [
        ...prev,
        { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'SUCCESS', module: 'pipeline.py', msg: 'Simulación de pipeline finalizada.' }
      ]);
      setActiveStep(-1);

      // Dispatch decoupled notification across system
      notify({
        title: 'Pipeline Lote POS-2026-B_M3 Procesado',
        message: 'Normalización estructural completada con 1,196 registros homologados listos para staging.',
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/revision'
      });
    }, 4200);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '11.5px', fontWeight: '600', letterSpacing: '0.08em', color: 'var(--color-slate-gray)', margin: '0 0 8px 0' }}>
          Fase 2: Procesamiento y Normalización
        </p>
        <h2 className="serif-display" style={{ fontSize: 'clamp(28px, 3.5vw, 36px)', margin: '0 0 16px 0', color: 'var(--color-ink-black)' }}>
          Pipeline de Homologación Estructural
        </h2>
        <button 
          className="btn-pill-dark" 
          onClick={simulateProcessing}
          type="button"
          style={{ padding: '10px 24px', fontSize: '14px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
        >
          <Play size={16} fill="currentColor" />
          Simular Nuevo Procesamiento
        </button>
      </header>

      {/* ── Workflow Stepper ── */}
      <div className="floating-artifact" style={{ padding: '32px 24px', marginBottom: '32px', overflowX: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '36px', minWidth: '700px' }}>
          <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
            Pipeline Workflow Execution Graph
          </h3>
          <span style={{ backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)', padding: '4px 12px', borderRadius: '9999px', fontSize: '12px', fontWeight: '600', fontFamily: 'var(--font-mono)' }}>
            Lote: POS-2026-B_M3
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', minWidth: '700px' }}>
          {/* Background Connector Line */}
          <div style={{ position: 'absolute', top: '21px', left: '40px', right: '40px', height: '2px', backgroundColor: 'var(--color-border)', zIndex: 0 }} />

          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = activeStep === -1 || activeStep > index;
            const isActive = activeStep === index + 1;

            return (
              <div key={step.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative', zIndex: 1, width: '110px' }}>
                <div 
                  className={`stepper-icon-wrap ${isCompleted ? 'completed' : ''} ${isActive ? 'active pulsing' : ''}`}
                  style={{ 
                    width: '42px', height: '42px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                    backgroundColor: isCompleted ? 'var(--color-alert-green)' : isActive ? '#3b82f6' : 'var(--color-paper-white)', 
                    color: isCompleted || isActive ? '#ffffff' : 'var(--color-slate-gray)',
                    border: isCompleted || isActive ? 'none' : '2px solid var(--color-border)',
                    boxShadow: isActive ? '0 0 0 4px rgba(59, 130, 246, 0.25)' : 'none',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onClick={() => alert(`Etapa: ${step.name}\nTiempo: ${step.time}\nDetalle: ${step.desc}`)}
                  title={`Etapa: ${step.name}`}
                >
                  <Icon size={18} />
                </div>
                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)' }}>{step.name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '4px' }}>
                    {isCompleted && <span style={{ color: 'var(--color-alert-green)' }}>✔</span>} {step.time}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '2px' }}>{step.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── KPI Summary Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Total Registros Procesados
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>1,248</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Registros Normalizados con Éxito
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-green)' }}>1,196</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)', border: '1px solid rgba(217, 56, 58, 0.3)', backgroundColor: 'rgba(217, 56, 58, 0.08)' }}>
          <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-alert-red)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Inconsistencias Estructurales
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-red)', marginBottom: '6px' }}>52</div>
          <div style={{ fontSize: '12px', color: 'var(--color-alert-red)' }}>Derivadas a Revisión Humana</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Tasa de Limpieza Automática
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>95.8%</div>
        </div>
      </div>

      {/* ── Console & Normalization Matrix ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', alignItems: 'start' }}>
        {/* Terminal Container */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: '600', margin: 0, color: 'var(--color-ink-black)' }}>
              <Terminal size={16} /> Consola de Ejecución en Tiempo Real
            </h3>
            <button 
              onClick={clearLogs} 
              type="button"
              style={{ background: 'none', border: 'none', color: 'var(--color-slate-gray)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', padding: '4px 8px', borderRadius: '6px' }}
              title="Limpiar registros de consola"
            >
              <Trash2 size={13} /> Limpiar Consola
            </button>
          </div>
          <div 
            ref={terminalContainerRef}
            className="terminal-container" 
            style={{ 
              backgroundColor: '#0c0e12', 
              borderRadius: '16px', 
              padding: '16px', 
              fontFamily: 'var(--font-mono)', 
              fontSize: '12.5px', 
              height: '320px', 
              overflowY: 'auto', 
              color: '#e2e8f0',
              border: '1px solid var(--color-border)',
              scrollbarWidth: 'thin'
            }}
          >
            {logs.length === 0 ? (
              <div style={{ color: 'var(--color-ash-gray)', fontStyle: 'italic', padding: '24px 0', textAlign: 'center' }}>
                Consola limpia. Presiona "Simular Nuevo Procesamiento" para ejecutar el pipeline.
              </div>
            ) : (
              logs.map((log, i) => (
                <div key={i} style={{ marginBottom: '8px', display: 'flex', gap: '10px', lineHeight: 1.4, flexWrap: 'wrap' }}>
                  <span style={{ color: '#718096' }}>[{log.time}]</span>
                  <span style={{ 
                    color: log.type === 'INFO' ? '#60a5fa' : log.type === 'WARN' ? '#f59e0b' : '#34d399',
                    minWidth: '54px',
                    fontWeight: 600
                  }}>
                    [{log.type}]
                  </span>
                  <span style={{ color: '#c084fc', minWidth: '95px' }}>{log.module}</span>
                  <span style={{ color: '#f1f5f9' }}>{log.msg}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Normalization Matrix */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600', margin: 0, color: 'var(--color-ink-black)' }}>
              Matriz de Normalización de Cabeceras
            </h3>
            <span style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
              Esquema Homologado
            </span>
          </div>
          <ResponsiveTable>
            <table className="steep-table">
              <thead>
                <tr>
                  <th>Original Cruda</th>
                  <th>Canónica Normalizada</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { o: 'NOMBRES Y APELLIDOS', n: 'nombre_completo', t: 'VARCHAR', r: 'Mapeo directo' },
                  { o: 'CALIF_FINAL', n: 'nota_final', t: 'NUMERIC', r: 'Conversión a float' },
                  { o: 'DOC_IDENTIDAD/CI', n: 'ci_estudiante', t: 'VARCHAR', r: 'Limpieza alfanumérica' },
                  { o: 'COD_MODULO', n: 'codigo_modulo', t: 'VARCHAR', r: 'Mapeo directo' },
                  { o: 'FECHA_EVAL', n: 'fecha_asentamiento', t: 'DATE', r: 'Parseo YYYY-MM-DD' },
                  { o: 'OBSERVACIONES', n: 'observacion', t: 'TEXT', r: 'Sanitizado HTML' }
                ].map((row, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>{row.o}</td>
                    <td style={{ fontWeight: 600, color: 'var(--color-sienna-brown)' }}>{row.n}</td>
                    <td>
                      <span style={{ backgroundColor: 'var(--color-mist-gray)', padding: '2px 6px', borderRadius: '4px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-ink-black)' }}>
                        {row.t}
                      </span>
                    </td>
                    <td>
                      <span className="badge-status badge-status-completed">
                        ✔ Mapeado
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ResponsiveTable>
        </div>
      </div>
    </div>
  );
}
