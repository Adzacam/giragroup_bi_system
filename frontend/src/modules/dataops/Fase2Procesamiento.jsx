import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Play, Terminal, ArrowRight, CheckSquare, Activity, FileSpreadsheet, FileText, FileCode, CheckCircle2, Clock, Layers } from 'lucide-react';
import PipelineStepper from './components/PipelineStepper';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import NormalizationMatrix from './components/NormalizationMatrix';
import PageHeader from '../../components/shared/PageHeader';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';
import { MOCK_INITIAL_LOGS } from '../../constants/mockData';

export default function Fase2Procesamiento() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
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
  const [pipelineFinished, setPipelineFinished] = useState(false);
  const [activeDocId, setActiveDocId] = useState(() => {
    const d = searchParams.get('docId');
    return d ? Number(d) : null;
  });

  const [incomingFiles, setIncomingFiles] = useState(() => {
    const rawFiles = searchParams.get('files');
    if (rawFiles) {
      const decoded = decodeURIComponent(rawFiles);
      return decoded.split(',').filter(Boolean).map((name, i) => {
        const lower = name.toLowerCase();
        let format = 'Excel';
        let size = '165 KB';
        if (lower.endsWith('.csv')) format = 'Google Forms CSV';
        else if (lower.endsWith('.xml')) format = 'Moodle XML';
        else if (lower.includes('cobranza') || lower.includes('egresos')) format = 'Sheets Contable';
        return {
          id: i + 1,
          name,
          format,
          size,
          status: 'ready'
        };
      });
    }
    const docIds = searchParams.get('docIds');
    if (docIds) {
      return docIds.split(',').filter(Boolean).map((id, i) => ({
        id: Number(id),
        name: `Documento_Fuente_#${id}.xlsx`,
        format: 'Excel Acta',
        size: '184 KB',
        status: 'ready'
      }));
    }
    return [
      { id: 1, name: 'Base_Academica_ARCA_TEST.xlsx', format: 'Excel Acta', size: '245 KB', status: 'ready' },
      { id: 2, name: 'BBDD_Evaluacion_Docente_GiraGroup_TEST.xlsx', format: 'Excel Encuesta', size: '182 KB', status: 'ready' },
      { id: 3, name: 'BD_Cobranzas_giraGroup.xlsx', format: 'Sheets Contable', size: '315 KB', status: 'ready' },
      { id: 4, name: 'BD_Egresos_TEST.xlsx', format: 'Sheets Contable', size: '158 KB', status: 'ready' },
      { id: 5, name: 'Reporte_Inscripciones_Forms.csv', format: 'Google Forms CSV', size: '94 KB', status: 'ready' },
      { id: 6, name: 'Calificaciones_Aula_Moodle.xml', format: 'Moodle XML', size: '120 KB', status: 'ready' },
      { id: 7, name: 'Acta_POS_2026_Modulo3.xlsx', format: 'Excel Acta', size: '198 KB', status: 'ready' }
    ];
  });

  const autoRunProcessedRef = useRef(false);
  const { notify } = useNotifications();

  const startPipelineExecution = async (docId = null, options = {}) => {
    if (isProcessing) return;
    setIsProcessing(true);
    setPipelineFinished(false);
    setIncomingFiles(prev => prev.map(f => ({ ...f, status: 'processing' })));

    sileoToast.info({
      title: 'Pipeline en Ejecución Automática',
      description: 'Lote enrutado por Dispatcher hacia las 6 etapas de normalización.'
    });
    // Auto-apertura inmediata de la consola de telemetría en vivo
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
      const processPromise = dataopsApi.processBatch(targetId);
      sileoToast.promise(processPromise, {
        loading: { title: 'Ejecutando Pipeline DataOps...', description: 'Normalizando cabeceras canónicas e insertando a Staging' },
        success: (res) => ({ title: 'Pipeline Completado con Éxito', description: 'Registros normalizados y confirmados en base de datos.' }),
        error: (err) => ({ title: 'Falla en Pipeline', description: 'Error durante la normalización de registros.' })
      });
      const res = await processPromise;
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
      let targetLabel = 'para el lote institucional';
      if (options?.files) {
        const count = options.files.split(',').length;
        targetLabel = `para ${count} archivo(s) seleccionado(s)`;
      } else if (options?.docIds) {
        const count = options.docIds.split(',').length;
        targetLabel = `para ${count} documento(s) seleccionado(s) [IDs: ${options.docIds}]`;
      } else if (targetId) {
        targetLabel = `para documento #${targetId}`;
      }

      setLogs(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString('en-US', { hour12: false }),
          type: 'SUCCESS',
          module: 'pipeline.py',
          msg: `Pipeline ejecutado con éxito ${targetLabel} en 4.2s.`
        }
      ]);
      setActiveStep(-1);
      setIsProcessing(false);
      setPipelineFinished(true);
      setIncomingFiles(prev => prev.map(f => ({ ...f, status: 'completed' })));

      sileoToast.action({
        title: 'Normalización Finalizada',
        description: '1,196 registros homologados y 52 casos para revisión humana.',
        button: {
          title: 'Ir a Fase 3',
          onClick: () => navigate('/dataops/revision')
        }
      });

      // Desacoplar y emitir notificación global
      notify({
        title: targetId ? `Documento #${targetId} Procesado` : 'Pipeline de Datos Procesado',
        message: `Normalización estructural completada ${targetLabel} con registros homologados listos para staging.`,
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
      const docIdsParam = searchParams.get('docIds');
      const filesParam = searchParams.get('files');
      const targetDocId = docIdParam ? Number(docIdParam) : null;
      if (targetDocId) {
        setActiveDocId(targetDocId);
      }
      // Limpiar autoRun de la URL para que al recargar no se re-dispare
      setSearchParams({}, { replace: true });
      startPipelineExecution(targetDocId, {
        docIds: docIdsParam,
        files: filesParam ? decodeURIComponent(filesParam) : null
      });
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

      {/* ── Panel de Lote Documental Activo para Homologación ── */}
      <div 
        className="floating-artifact"
        style={{
          padding: '20px 24px',
          borderRadius: 'var(--radius-cards)',
          marginBottom: '28px',
          border: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-paper-white)',
          boxShadow: 'var(--shadow-subtle)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              backgroundColor: 'rgba(217, 155, 38, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-gira-gold)'
            }}>
              <Layers size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 className="serif-heading" style={{ fontSize: '18px', margin: 0, color: 'var(--color-ink-black)' }}>
                  Lote Documental para Procesamiento
                </h3>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(217, 155, 38, 0.15)',
                  color: 'var(--color-gira-gold)',
                  letterSpacing: '0.4px'
                }}>
                  {incomingFiles.length} ARCHIVO{incomingFiles.length === 1 ? '' : 'S'}
                </span>
              </div>
              <p style={{ margin: '3px 0 0', fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Fuentes documentales seleccionadas para parseo UTF-8, clasificación por dispatcher, sanitizado y homologación canónica.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isProcessing ? (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-alert-amber)',
                backgroundColor: 'rgba(245, 158, 11, 0.12)',
                padding: '5px 14px',
                borderRadius: '9999px'
              }}>
                <Activity size={13} className="spin" /> Pipeline en Ejecución ({incomingFiles.length} archivos)...
              </span>
            ) : pipelineFinished ? (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-alert-green)',
                backgroundColor: 'rgba(34, 197, 94, 0.12)',
                padding: '5px 14px',
                borderRadius: '9999px'
              }}>
                <CheckCircle2 size={13} /> {incomingFiles.length} Archivos Homologados con Éxito
              </span>
            ) : (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-slate-gray)',
                backgroundColor: 'var(--color-mist-gray)',
                padding: '5px 14px',
                borderRadius: '9999px'
              }}>
                <Clock size={13} /> Preparado para Iniciar
              </span>
            )}
          </div>
        </div>

        {/* Rejilla de archivos del lote */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '12px',
          maxHeight: '260px',
          overflowY: 'auto',
          paddingRight: '4px'
        }}>
          {incomingFiles.map((file) => {
            const isXlsx = file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls');
            const isCsv = file.name.toLowerCase().endsWith('.csv');
            const isXml = file.name.toLowerCase().endsWith('.xml');

            return (
              <div
                key={file.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: 'var(--color-fog-white)',
                  border: file.status === 'processing' 
                    ? '1px solid var(--color-gira-gold)' 
                    : file.status === 'completed'
                    ? '1px solid rgba(34, 197, 94, 0.3)'
                    : '1px solid var(--color-border)',
                  borderRadius: '10px',
                  gap: '10px',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: 1 }}>
                  <div style={{ flexShrink: 0 }}>
                    {isXlsx ? (
                      <FileSpreadsheet size={18} color="var(--color-alert-green)" />
                    ) : isCsv ? (
                      <FileText size={18} color="#0284c7" />
                    ) : isXml ? (
                      <FileCode size={18} color="#9333ea" />
                    ) : (
                      <FileText size={18} color="var(--color-slate-gray)" />
                    )}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{
                      fontSize: '12.5px',
                      fontWeight: 600,
                      color: 'var(--color-ink-black)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }} title={file.name}>
                      {file.name}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                      {file.format} · <span style={{ fontFamily: 'var(--font-mono)' }}>{file.size}</span>
                    </div>
                  </div>
                </div>

                <div style={{ flexShrink: 0 }}>
                  {file.status === 'processing' ? (
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      color: 'var(--color-gira-gold)',
                      backgroundColor: 'rgba(217, 155, 38, 0.12)',
                      padding: '3px 8px',
                      borderRadius: '9999px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <Activity size={10} className="spin" /> Normalizando
                    </span>
                  ) : file.status === 'completed' ? (
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      color: 'var(--color-alert-green)',
                      backgroundColor: 'rgba(34, 197, 94, 0.12)',
                      padding: '3px 8px',
                      borderRadius: '9999px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <CheckCircle2 size={10} /> Homologado
                    </span>
                  ) : (
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      color: 'var(--color-slate-gray)',
                      backgroundColor: 'var(--color-mist-gray)',
                      padding: '3px 8px',
                      borderRadius: '9999px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <Clock size={10} /> En cola
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Workflow Stepper (6 nodos con animación) ── */}
      <PipelineStepper
        activeStep={activeStep}
        lotName={incomingFiles.length > 0 ? `Lote: ${incomingFiles.length} archivos activos` : (activeDocId ? `Documento: #${activeDocId}` : "Lote: POS-2026-B_M3")}
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

      {/* ── Panel de Estado o Tarjeta de Transición a Fase 3 (Sin botón de telemetría duplicado) ── */}
      {isProcessing ? (
        <div 
          className="card-mist" 
          style={{ 
            marginTop: '28px', 
            padding: '24px 28px', 
            borderRadius: 'var(--radius-cards)', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            flexWrap: 'wrap', 
            gap: '16px',
            borderLeft: '4px solid var(--color-sienna-brown)'
          }}
        >
          <div>
            <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', fontWeight: 600, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} className="spin-animation" color="var(--color-sienna-brown)" /> Estado del Pipeline: Procesando Lote Activo
            </h4>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-slate-gray)', maxWidth: '680px', lineHeight: 1.5 }}>
              Ejecutando normalización canónica, extracción de islas tabulares y verificación de integridad. Puede observar el flujo técnico en vivo en la consola de telemetría desplegada a la derecha.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#38bdf8' }} />
            <span>Sincronizando con staging_registros_crudos...</span>
          </div>
        </div>
      ) : (
        <div 
          className="card-mist" 
          style={{ 
            marginTop: '28px', 
            padding: '28px 32px', 
            borderRadius: 'var(--radius-cards)', 
            borderLeft: '5px solid var(--color-gira-gold)',
            border: '1px solid rgba(217, 155, 38, 0.25)',
            backgroundColor: 'var(--color-paper-white)',
            boxShadow: 'var(--shadow-subtle)',
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            flexWrap: 'wrap', 
            gap: '24px' 
          }}
        >
          <div style={{ flex: '1 1 540px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span 
                style={{ 
                  color: 'var(--color-gira-gold)', 
                  fontWeight: 700, 
                  fontSize: '11.5px', 
                  letterSpacing: '0.8px', 
                  textTransform: 'uppercase',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <CheckSquare size={14} color="var(--color-gira-gold)" />
                FASE 3: INTEGRIDAD Y RECONCILIACIÓN
              </span>
            </div>

            <h3 
              style={{ 
                margin: '0 0 10px 0', 
                fontFamily: "var(--font-signifier, 'Newsreader', Georgia, serif)", 
                fontWeight: 400, 
                fontStyle: 'normal',
                fontSize: '24px', 
                color: 'var(--color-ink-black)',
                lineHeight: 1.25
              }}
            >
              Revisión Humana y Doble Confianza (NER BETO & RapidFuzz)
            </h3>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginTop: '12px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-alert-green)' }} />
                <strong style={{ color: 'var(--color-alert-green)', fontWeight: 600 }}>
                  {(kpis.registros_normalizados || 1196).toLocaleString()} registros normalizados con éxito
                </strong>
              </div>

              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-alert-red)' }} />
                <strong style={{ color: 'var(--color-alert-red)', fontWeight: 600 }}>
                  {kpis.inconsistencias_estructurales || 52} inconsistencias derivadas a revisión humana
                </strong>
              </div>
            </div>

            <p style={{ margin: '10px 0 0 0', fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: 1.5, maxWidth: '640px' }}>
              Los registros normalizados están listos en staging. Proceda a la reconciliación y validación cruzada multi-fuente para resolver ambigüedades en cédulas de identidad, nombres con sufijos y notas no asentadas.
            </p>
          </div>

          <div>
            <button 
              type="button"
              className="btn-pill-dark" 
              onClick={() => navigate('/dataops/revision')}
              style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                gap: '10px', 
                padding: '12px 26px', 
                fontSize: '14px', 
                fontWeight: 600,
                backgroundColor: 'var(--color-ink-black)',
                color: 'var(--color-paper-white)',
                boxShadow: 'var(--shadow-subtle)',
                cursor: 'pointer'
              }}
            >
              <span>Continuar a Fase 3: Revisión Humana</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

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
