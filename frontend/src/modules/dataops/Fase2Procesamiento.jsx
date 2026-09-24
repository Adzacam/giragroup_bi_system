import React, { useState } from 'react';
import { Play } from 'lucide-react';
import PipelineStepper from './components/PipelineStepper';
import TerminalConsole from './components/TerminalConsole';
import NormalizationMatrix from './components/NormalizationMatrix';
import { dataopsApi } from '../../api/dataopsApi';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';
import { MOCK_INITIAL_LOGS } from '../../constants/mockData';

export default function Fase2Procesamiento() {
  const [activeStep, setActiveStep] = useState(-1);
  const [logs, setLogs] = useState(MOCK_INITIAL_LOGS);
  const [kpis, setKpis] = useState({
    total_registros_procesados: 1248,
    registros_normalizados: 1196,
    inconsistencias_estructurales: 52,
    tasa_limpieza: 95.8
  });
  const [matrix, setMatrix] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const { notify } = useNotifications();

  const simulateProcessing = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setActiveStep(0);
    setLogs([]);

    const delays = [300, 800, 1500, 2200, 2900, 3600];
    const logMessages = [
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'parser.py', msg: 'Parseo UTF-8 en progreso...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'dispatcher.py', msg: 'Enrutando archivo por extensión y firmas binarias...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'cleaner.py', msg: 'Limpieza estructural y detección de islas tabulares...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'INFO', module: 'mapper.py', msg: 'Normalizando cabeceras a esquema canónico dimensional...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'WARN', module: 'validator.py', msg: 'Validación de esquema (95.8% validez, 52 casos a revisión)...' },
      { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'SUCCESS', module: 'loader.py', msg: 'Inserción a staging_registros_crudos completada.' }
    ];

    delays.forEach((delay, index) => {
      setTimeout(() => {
        setActiveStep(index + 1);
        setLogs(prev => [...prev, logMessages[index]]);
      }, delay);
    });

    try {
      // Invocación a backend
      const res = await dataopsApi.processBatch();
      if (res && res.kpis) {
        setKpis(res.kpis);
      }
      if (res && res.normalization_matrix) {
        setMatrix(res.normalization_matrix);
      }
    } catch (err) {
      console.warn('Ejecutando en modo simulación:', err);
    }

    setTimeout(() => {
      setLogs(prev => [
        ...prev,
        { time: new Date().toLocaleTimeString('en-US', { hour12: false }), type: 'SUCCESS', module: 'pipeline.py', msg: 'Pipeline ejecutado con éxito en 4.2s.' }
      ]);
      setActiveStep(-1);
      setIsProcessing(false);

      // Desacoplar y emitir notificación global
      notify({
        title: 'Pipeline Lote POS-2026-B_M3 Procesado',
        message: 'Normalización estructural completada con 1,196 registros homologados listos para staging.',
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/revision'
      });
    }, 4200);
  };

  const handleClearLogs = () => {
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
          disabled={isProcessing}
          type="button"
          style={{ padding: '10px 24px', fontSize: '14px', display: 'inline-flex', alignItems: 'center', gap: '8px', opacity: isProcessing ? 0.6 : 1 }}
        >
          <Play size={16} fill="currentColor" />
          {isProcessing ? 'Procesando pipeline...' : 'Simular Nuevo Procesamiento'}
        </button>
      </header>

      {/* ── Workflow Stepper (6 nodos con animación) ── */}
      <PipelineStepper
        activeStep={activeStep}
        lotName="Lote: POS-2026-B_M3"
      />

      {/* ── KPI Summary Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Total Registros Procesados
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>
            {(kpis.total_registros_procesados || 1248).toLocaleString()}
          </div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Registros Normalizados con Éxito
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-green)' }}>
            {(kpis.registros_normalizados || 1196).toLocaleString()}
          </div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)', border: '1px solid rgba(217, 56, 58, 0.3)', backgroundColor: 'rgba(217, 56, 58, 0.08)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-alert-red)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Inconsistencias Estructurales
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-red)', marginBottom: '6px' }}>
            {kpis.inconsistencias_estructurales || 52}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-alert-red)' }}>Derivadas a Revisión Humana</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Tasa de Limpieza Automática
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>
            {kpis.tasa_limpieza || 95.8}%
          </div>
        </div>
      </div>

      {/* ── Console & Normalization Matrix ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', alignItems: 'start' }}>
        <TerminalConsole
          logs={logs}
          onClear={handleClearLogs}
          isStreaming={isProcessing}
        />

        <NormalizationMatrix
          matrix={matrix}
        />
      </div>
    </div>
  );
}
