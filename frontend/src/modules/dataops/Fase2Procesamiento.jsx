import React, { useState, useEffect, useRef } from 'react';
import { Play, FileUp, Split, Wand2, TableProperties, ShieldCheck, Database, Terminal, Trash2 } from 'lucide-react';

export default function Fase2Procesamiento() {
  const [activeStep, setActiveStep] = useState(-1);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  const initialLogs = [
    { time: '10:15:02', type: 'INFO', module: 'dispatcher.py', msg: 'Iniciando pipeline para lote POS-2026-B_M3' },
    { time: '10:15:03', type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 completado (342 filas)' },
    { time: '10:15:04', type: 'INFO', module: 'cleaner.py', msg: 'Sanitizado de caracteres especiales finalizado' },
    { time: '10:15:05', type: 'INFO', module: 'mapper.py', msg: 'Mapeo de 12 columnas a esquema canónico' },
    { time: '10:15:06', type: 'WARN', module: 'validator.py', msg: '52 registros con inconsistencias estructurales detectados' },
    { time: '10:15:07', type: 'SUCCESS', module: 'pipeline.py', msg: '1,196 registros listos para staging' },
    { time: '10:15:08', type: 'INFO', module: 'loader.py', msg: 'Batch INSERT a esquema staging completado' },
    { time: '10:15:09', type: 'SUCCESS', module: 'pipeline.py', msg: 'Pipeline ejecutado con éxito en 4.2s' }
  ];

  useEffect(() => {
    if (activeStep === -1) {
      setLogs(initialLogs);
    }
    // Scroll to bottom of logs
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, activeStep]);

  const simulateProcessing = () => {
    setActiveStep(0);
    setLogs([]);
    const delays = [300, 800, 1500, 2200, 2900, 3600];
    const logMessages = [
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 en progreso...' },
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'INFO', module: 'dispatcher.py', msg: 'Enrutando archivo Acta_POS...' },
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'INFO', module: 'cleaner.py', msg: 'Limpieza y sanitizado de datos...' },
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'INFO', module: 'mapper.py', msg: 'Normalizando cabeceras...' },
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'WARN', module: 'validator.py', msg: 'Validación de esquema (95.8% validez)...' },
      { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'SUCCESS', module: 'loader.py', msg: 'Inserción a Staging completada.' }
    ];

    delays.forEach((delay, index) => {
      setTimeout(() => {
        setActiveStep(index + 1);
        setLogs(prev => [...prev, logMessages[index]]);
      }, delay);
    });
    
    setTimeout(() => {
      setLogs(prev => [...prev, { time: new Date().toLocaleTimeString('en-US', {hour12: false}), type: 'SUCCESS', module: 'pipeline.py', msg: 'Simulación finalizada.' }]);
    }, 4000);
  };

  const clearLogs = () => setLogs([]);

  const steps = [
    { id: 1, name: 'Archivo Origen', time: '45ms', desc: 'Parseo UTF-8', icon: FileUp },
    { id: 2, name: 'Dispatcher', time: '110ms', desc: 'Acta_POS', icon: Split },
    { id: 3, name: 'Limpieza', time: '310ms', desc: 'Sanitizado', icon: Wand2 },
    { id: 4, name: 'Cabeceras', time: '140ms', desc: '12 Columnas', icon: TableProperties },
    { id: 5, name: 'Esquema', time: '195ms', desc: '95.8% Validez', icon: ShieldCheck },
    { id: 6, name: 'A Staging', time: '85ms', desc: 'INSERT batch', icon: Database },
  ];

  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '12px', fontWeight: '600', letterSpacing: '0.05em', color: '#666' }}>
          Fase 2: Procesamiento y Normalización
        </p>
        <h2 className="serif-display" style={{ fontFamily: 'Newsreader, serif', fontSize: '32px', marginTop: '8px', marginBottom: '16px', color: '#17191c' }}>
          Pipeline de Homologación Estructural
        </h2>
        <button 
          className="btn-pill-dark" 
          onClick={simulateProcessing}
          style={{ backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '10px 24px', border: 'none', cursor: 'pointer', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Play size={18} fill="currentColor" />
          Simular Nuevo Procesamiento
        </button>
      </header>

      <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '24px', padding: '32px', marginBottom: '32px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', margin: 0, color: '#4a5568' }}>Pipeline Workflow Execution Graph</h3>
          <span style={{ backgroundColor: '#edf2f7', color: '#4a5568', padding: '4px 12px', borderRadius: '9999px', fontSize: '12px', fontWeight: '600', fontFamily: 'JetBrains Mono, monospace' }}>Lote: POS-2026-B_M3</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
          {/* Background Connector Line */}
          <div style={{ position: 'absolute', top: '21px', left: '40px', right: '40px', height: '2px', backgroundColor: '#e2e8f0', zIndex: 0 }}></div>
          
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = activeStep > index || activeStep === -1;
            const isActive = activeStep === index + 1;
            
            return (
              <div key={step.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative', zIndex: 1, width: '120px' }}>
                <div 
                  className={`stepper-icon-wrap ${isCompleted ? 'completed' : ''} ${isActive ? 'active pulsing' : ''}`}
                  style={{ 
                    width: '42px', height: '42px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                    backgroundColor: isCompleted ? '#38a169' : isActive ? '#3182ce' : '#fff', 
                    color: isCompleted || isActive ? '#fff' : '#a0aec0',
                    border: isCompleted || isActive ? 'none' : '2px solid #e2e8f0',
                    boxShadow: isActive ? '0 0 0 4px rgba(49,130,206,0.2)' : 'none',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onClick={() => alert(`Etapa: ${step.name}\nTiempo: ${step.time}\nDetalle: ${step.desc}`)}
                >
                  <Icon size={20} />
                </div>
                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#17191c' }}>{step.name}</div>
                  <div style={{ fontSize: '11px', color: '#718096', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '4px' }}>
                    {isCompleted && <span style={{ color: '#38a169' }}>✔</span>} {step.time}
                  </div>
                  <div style={{ fontSize: '11px', color: '#a0aec0', marginTop: '2px' }}>{step.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: '0 0 16px 0' }}>Total Registros Procesados</h3>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#17191c' }}>1,248</div>
        </div>
        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: '0 0 16px 0' }}>Registros Normalizados con Éxito</h3>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#38a169' }}>1,196</div>
        </div>
        <div className="card-mist" style={{ backgroundColor: '#fff5f5', padding: '24px', borderRadius: '24px', border: '1px solid #feb2b2' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#c53030', margin: '0 0 16px 0' }}>Inconsistencias Estructurales</h3>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#e53e3e', marginBottom: '8px' }}>52</div>
          <div style={{ fontSize: '13px', color: '#c53030' }}>Derivadas a Revisión Humana</div>
        </div>
        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: '0 0 16px 0' }}>Tasa de Limpieza Automática</h3>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#17191c' }}>95.8%</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: '600', margin: 0 }}>
              <Terminal size={18} /> Consola de Ejecución en Tiempo Real (pipeline.py)
            </h3>
            <button onClick={clearLogs} style={{ background: 'none', border: 'none', color: '#718096', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
              <Trash2 size={14} /> Limpiar Consola
            </button>
          </div>
          <div className="terminal-container" style={{ backgroundColor: '#0f1113', borderRadius: '16px', padding: '16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', height: '290px', overflowY: 'auto', color: '#e2e8f0' }}>
            {logs.map((log, i) => (
              <div key={i} style={{ marginBottom: '8px', display: 'flex', gap: '12px' }}>
                <span style={{ color: '#718096' }}>[{log.time}]</span>
                <span style={{ 
                  color: log.type === 'INFO' ? '#63b3ed' : log.type === 'WARN' ? '#ecc94b' : '#68d391',
                  minWidth: '60px'
                }}>
                  [{log.type}]
                </span>
                <span style={{ color: '#b794f4', minWidth: '110px' }}>{log.module}</span>
                <span>{log.msg}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>

        <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '24px', padding: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', margin: 0 }}>Matriz de Normalización de Cabeceras</h3>
            <span style={{ backgroundColor: '#ebf8ff', color: '#2b6cb0', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500' }}>Esquema Homologado</span>
          </div>
          <table className="steep-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#4a5568' }}>
                <th style={{ padding: '12px 8px', fontWeight: '600' }}>Original Cruda</th>
                <th style={{ padding: '12px 8px', fontWeight: '600' }}>Canónica Normalizada</th>
                <th style={{ padding: '12px 8px', fontWeight: '600' }}>Tipo</th>
                <th style={{ padding: '12px 8px', fontWeight: '600' }}>Estado</th>
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
                <tr key={i} style={{ borderBottom: '1px solid #f7fafc' }}>
                  <td style={{ padding: '12px 8px', fontFamily: 'JetBrains Mono, monospace', color: '#718096', fontSize: '12px' }}>{row.o}</td>
                  <td style={{ padding: '12px 8px', fontWeight: '600', color: '#8b4513' }}>{row.n}</td>
                  <td style={{ padding: '12px 8px' }}><span style={{ backgroundColor: '#edf2f7', padding: '2px 6px', borderRadius: '4px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{row.t}</span></td>
                  <td style={{ padding: '12px 8px' }}><span className="badge-status-completed" style={{ color: '#38a169', fontWeight: '500', fontSize: '12px' }}>✔ Mapeado</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
