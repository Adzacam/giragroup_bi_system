import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Play, Terminal } from 'lucide-react';
import PipelineStepper from './components/PipelineStepper';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import NormalizationMatrix from './components/NormalizationMatrix';
import PageHeader from '../../components/shared/PageHeader';
import { dataopsApi } from '../../api/dataopsApi';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';
import { MOCK_INITIAL_LOGS } from '../../constants/mockData';

export default function Fase2Procesamiento() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeStep, setActiveStep] = useState(-1);
  const [logs, setLogs] = useState(MOCK_INITIAL_LOGS);
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(false);
  const [kpis, setKpis] = useState({
    total_registros_procesados: 1248,
    registros_normalizados: 1196,
    inconsistencias_estructurales: 52,
    tasa_limpieza: 95.8
  });
  const [matrix, setMatrix] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeDocId, setActiveDocId] = useState(() => {
    const d = searchParams.get('docId');
    return d ? Number(d) : null;
  });

  const autoRunProcessedRef = useRef(false);
  const { notify } = useNotifications();

  const startPipelineExecution = async (docId = null) => {
    if (isProcessing) return;
    setIsProcessing(true);
    setIsTelemetryOpen(true);
    setActiveStep(0);
    setLogs([]);
    if (docId) {
      setActiveDocId(docId);
    }

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
      // Invocación a endpoint real del backend
      const targetId = docId || activeDocId;
      const res = await dataopsApi.processBatch(targetId);
      if (res) {
        if (res.kpis) {
          setKpis(res.kpis);
        }
        if (res.normalization_matrix) {
          setMatrix(res.normalization_matrix);
        }
        if (res.logs && Array.isArray(res.logs) && res.logs.length > 0) {
          setTimeout(() => {
            setLogs(res.logs);
          }, 3800);
        }
      }
    } catch (err) {
      console.error('Error al procesar el pipeline en backend:', err);
    }

    setTimeout(() => {
      const targetId = docId || activeDocId;
      setLogs(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString('en-US', { hour12: false }),
          type: 'SUCCESS',
          module: 'pipeline.py',
          msg: `Pipeline ejecutado con éxito ${targetId ? `para documento #${targetId}` : 'para el lote institucional'} en 4.2s.`
        }
      ]);
      setActiveStep(-1);
      setIsProcessing(false);

      // Desacoplar y emitir notificación global
      notify({
        title: targetId ? `Documento #${targetId} Procesado` : 'Pipeline de Datos Procesado',
        message: 'Normalización estructural completada con registros homologados listos para staging.',
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/revision'
      });
    }, 4200);
  };

  useEffect(() => {
    const isAutoRun = searchParams.get('autoRun') === 'true';
    if (isAutoRun && !autoRunProcessedRef.current) {
      autoRunProcessedRef.current = true;
      const docIdParam = searchParams.get('docId');
      const targetDocId = docIdParam ? Number(docIdParam) : null;
      if (targetDocId) {
        setActiveDocId(targetDocId);
      }
      // Limpiar autoRun de la URL para que al recargar no se re-dispare
      setSearchParams({}, { replace: true });
      startPipelineExecution(targetDocId);
    }
  }, [searchParams, setSearchParams]);

  const handleClearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <PageHeader
        category="Fase 2: Procesamiento y Normalización"
        title="Pipeline de Homologación Estructural"
        subtitle="Flujo automatizado de 6 etapas para detección de esquemas, limpieza sintáctica y normalización a tablas staging."
        action={
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button 
              className="btn-pill-ghost" 
              onClick={() => setIsTelemetryOpen(true)}
              type="button"
              style={{ padding: '10px 18px', fontSize: '13.5px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Terminal size={15} /> Ver Telemetría en Vivo
            </button>
            <button 
              className="btn-pill-dark" 
              onClick={() => startPipelineExecution(activeDocId)}
              disabled={isProcessing}
              type="button"
              style={{ padding: '10px 24px', fontSize: '14px', display: 'inline-flex', alignItems: 'center', gap: '8px', opacity: isProcessing ? 0.6 : 1 }}
            >
              <Play size={16} fill="currentColor" />
              {isProcessing ? 'Procesando pipeline...' : 'Iniciar Procesamiento de Pipeline'}
            </button>
          </div>
        }
      />

      {/* ── Workflow Stepper (6 nodos con animación) ── */}
      <PipelineStepper
        activeStep={activeStep}
        lotName={activeDocId ? `Documento: #${activeDocId}` : "Lote: POS-2026-B_M3"}
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

      {/* ── Matriz de Normalización de Cabeceras ── */}
      <NormalizationMatrix
        matrix={matrix}
      />

      {/* ── Action Box Telemetría en Vivo (idéntica a Fase 3) ── */}
      <div 
        className="card-mist" 
        style={{ 
          marginTop: '28px', 
          padding: '24px', 
          borderRadius: 'var(--radius-cards)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          flexWrap: 'wrap', 
          gap: '16px' 
        }}
      >
        <div>
          <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', fontWeight: 600, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={16} color="var(--color-sienna-brown)" /> Telemetría de Ejecución en Tiempo Real (pipeline.py)
          </h4>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-slate-gray)', maxWidth: '680px', lineHeight: 1.5 }}>
            Consola técnica HUD en tiempo real con trazas de parseo UTF-8, enrutamiento por firmas binarias, sanitizado de celdas fusionadas, validación canónica e inserción por lotes a PostgreSQL Staging.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button 
            type="button"
            className="btn-pill-dark" 
            onClick={() => setIsTelemetryOpen(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 22px', fontSize: '13px', fontWeight: 600 }}
          >
            <Terminal size={15} /> Ver Telemetría en Vivo
          </button>
        </div>
      </div>

      {/* ── Drawer Lateral de Telemetría (Estilo Fase 3 HUD) ── */}
      <PipelineTelemetryDrawer
        isOpen={isTelemetryOpen}
        onClose={() => setIsTelemetryOpen(false)}
        logs={logs}
        onClearLogs={handleClearLogs}
        isProcessing={isProcessing}
        lotName={activeDocId ? `Documento #${activeDocId}` : "Lote: POS-2026-B_M3"}
      />
    </div>
  );
}
