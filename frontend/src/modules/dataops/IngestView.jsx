import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle, Play,
  HelpCircle, Eye, RefreshCw, Trash2, Check, Scale, Terminal,
  Calendar, ShieldCheck, Sliders, ChevronDown, ChevronUp, X, Sparkles, ArrowRight, FileText
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import { dataopsApi } from '../../api/dataopsApi';
import { catalogApi } from '../../api/catalogApi';
import { useCatalogProgramCount } from '../../hooks/useCatalogProgramCount';
import { sileoToast } from '../../services/sileoToast';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import {
  inspectFileHeaders,
  validateFileSecurityClient,
  isAcademicSourceType,
  toCanonicalSourceCode,
  formatFileSize,
  UNRECOGNIZED_SOURCE_LABEL,
} from '../../utils/fileTypeDetector';
import {
  MAX_ARCHIVOS_POR_LOTE,
  MAX_TAMANO_ARCHIVO_MB,
  ESCALAS_ACADEMICAS,
  TIPOS_FUENTE_DATAOPS,
} from '../../constants/dataopsConfig';

export default function IngestView() {
  const navigate = useNavigate();
  const totalProgramas = useCatalogProgramCount();

  // ─── Estado de la cola multi-archivo (Sección A) ───
  const [queuedFiles, setQueuedFiles] = useState([]);
  const [institucion, setInstitucion] = useState('GiraGroup Posgrado');
  const [umbralConfianzaIa, setUmbralConfianzaIa] = useState(85);
  const [anonimizacionActiva, setAnonimizacionActiva] = useState(true);
  const [escalaGlobalAcademica, setEscalaGlobalAcademica] = useState('CENTESIMAL_100');

  // ─── Estados de Proceso e Historial ───
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStageText, setUploadStageText] = useState('');
  const [sourcesHistory, setSourcesHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [historyExpanded, setHistoryExpanded] = useState(false);

  // ─── Estado de Lote Activo para Sección B y Sección C (Split View) ───
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [activeBatchData, setActiveBatchData] = useState(null);
  const [lastUploadedBatchId, setLastUploadedBatchId] = useState(null);
  const [selectedInspectionIndex, setSelectedInspectionIndex] = useState(0);
  const [isLoadingBatchData, setIsLoadingBatchData] = useState(false);

  // ─── Estados del Drawer de Bitácora Técnica y Reporte Markdown (.MD) ───
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [telemetryDoc, setTelemetryDoc] = useState(null);
  const [telemetryLogs, setTelemetryLogs] = useState([]);
  const [telemetryMarkdown, setTelemetryMarkdown] = useState('');
  const [telemetryMetrics, setTelemetryMetrics] = useState(null);

  const loadInitialData = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await dataopsApi.getSources();
      if (res && res.data) {
        setSourcesHistory(res.data);
      }

      const lastId = localStorage.getItem('last_active_batch_id');
      if (lastId && res?.data?.some(d => String(d.id_lote || d.id) === String(lastId))) {
        setActiveBatchId(Number(lastId));
        await loadBatchInspection(Number(lastId));
      } else {
        localStorage.removeItem('last_active_batch_id');
        setActiveBatchId(null);
        setActiveBatchData(null);
      }
    } catch (err) {
      console.warn('Error al cargar datos iniciales de ingesta:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadBatchInspection = async (batchId) => {
    if (!batchId) return;
    try {
      setIsLoadingBatchData(true);
      const batchRes = await dataopsApi.getLoteRawVsText(batchId);
      if (batchRes && batchRes.registros) {
        setActiveBatchData(batchRes);
      }
    } catch (err) {
      console.warn('No se pudo cargar datos del lote:', err);
    } finally {
      setIsLoadingBatchData(false);
    }
  };

  const handleOpenTelemetry = async (src) => {
    const docId = src?.id_documento || src?.id || src?.id_lote || 1;
    const normalizedSrc = src
      ? {
          ...src,
          id: src.id || src.id_documento || docId,
          name: src.name || src.nombre_archivo || `Documento_${docId}`,
          nombre_archivo: src.nombre_archivo || src.name || `Documento_${docId}`,
          type: src.type || src.tipo_fuente || src.tipo_documento || 'ACTA',
          records: src.records ?? src.registros_detectados ?? src.total_registros ?? 0,
        }
      : { id: docId, name: 'Lote Activo', nombre_archivo: 'Lote Activo', type: 'ACTA', records: 0 };
    setTelemetryDoc(normalizedSrc);
    setTelemetryOpen(true);
    try {
      const res = await dataopsApi.getLogs(docId);
      if (res) {
        setTelemetryLogs(res.data || []);
        setTelemetryMarkdown(res.markdown_report || '');
        setTelemetryMetrics(res.summary_metrics || null);
      }
    } catch (err) {
      console.warn('Error al obtener bitácora técnica:', err);
    }
  };

  const mapSourceToOriginCode = (srcType, fileName = '') => {
    const code = toCanonicalSourceCode(srcType);
    const fn = (fileName || '').toLowerCase();
    if (code === 'MOODLE' || fn.includes('moodle')) return 'MOODLE_EXPORT';
    if (code === 'COBRANZA' || fn.includes('cobranza') || fn.includes('cartera')) return 'GFORMS_ADM_PAGOS';
    if (code === 'ADMISION' || fn.includes('admision') || fn.includes('inscrip')) return 'GFORMS_ADM_PAGOS';
    if (fn.includes('asist')) return 'GSHEETS_ACTA_ASIST';
    return 'GSHEETS_ACTA_NOTAS';
  };

  const addFilesToQueue = async (fileList) => {
    const incoming = Array.from(fileList || []);
    if (incoming.length === 0) return;

    if (queuedFiles.length + incoming.length > MAX_ARCHIVOS_POR_LOTE) {
      sileoToast.error({
        title: 'Límite de archivos por lote excedido',
        description: `Se permiten máximo ${MAX_ARCHIVOS_POR_LOTE} archivos simultáneos por lote.`,
      });
      return;
    }

    const validItems = [];
    for (const f of incoming) {
      const sec = validateFileSecurityClient(f);
      if (!sec.valid) {
        sileoToast.error({
          title: 'Archivo rechazado por validación',
          description: sec.error,
        });
        continue;
      }

      // Inspección prioritaria de cabeceras reales
      const headerResult = await inspectFileHeaders(f);
      const canonicalCode = headerResult.recognized ? toCanonicalSourceCode(headerResult.code) : '';
      const originCode = mapSourceToOriginCode(canonicalCode, f.name);

      validItems.push({
        uid: `${f.name}_${f.size}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        file: f,
        sourceType: canonicalCode,
        originDetected: originCode,
        recognized: headerResult.recognized,
        matchedKeywords: headerResult.matchedKeywords || [],
        tipoEscala: isAcademicSourceType(canonicalCode) ? (escalaGlobalAcademica || 'CENTESIMAL_100') : null,
        filasEstimadas: Math.max(12, Math.round(f.size / 180)),
        fechasReconocidas: 'Por detectar',
        sha256Ok: true,
        status: 'En cola',
        statusDetail: '',
      });
    }

    if (validItems.length > 0) {
      setQueuedFiles((prev) => [...prev, ...validItems]);
      const unrecognizedCount = validItems.filter((it) => !it.sourceType).length;
      if (unrecognizedCount > 0) {
        sileoToast.warning({
          title: `${unrecognizedCount} archivo(s) sin tipo reconocido`,
          description: 'Seleccione manualmente el tipo documental en los selectores correspondientes.',
        });
      } else {
        sileoToast.success({
          title: `${validItems.length} archivo(s) añadido(s) al lote`,
          description: 'Cabeceras y tipo documental verificados automáticamente.',
        });
      }
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFilesToQueue(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFilesToQueue(e.target.files);
      e.target.value = '';
    }
  };

  const handleRemoveFile = (uid) => {
    setQueuedFiles((prev) => prev.filter((item) => item.uid !== uid));
  };

  const handleChangeFileSourceType = (uid, newCode) => {
    setQueuedFiles((prev) =>
      prev.map((item) => {
        if (item.uid !== uid) return item;
        const academic = isAcademicSourceType(newCode);
        const originCode = mapSourceToOriginCode(newCode, item.file.name);
        return {
          ...item,
          sourceType: newCode,
          originDetected: originCode,
          tipoEscala: academic ? (item.tipoEscala || escalaGlobalAcademica || 'CENTESIMAL_100') : null,
          status: 'En cola',
          statusDetail: '',
        };
      })
    );
  };

  // Validaciones del lote
  const missingSourceTypeCount = queuedFiles.filter((it) => !it.sourceType).length;
  const missingScaleCount = queuedFiles.filter(
    (it) => isAcademicSourceType(it.sourceType) && !it.tipoEscala
  ).length;

  const isFormValid =
    queuedFiles.length > 0 &&
    queuedFiles.length <= MAX_ARCHIVOS_POR_LOTE &&
    Boolean(institucion) &&
    missingSourceTypeCount === 0 &&
    missingScaleCount === 0;

  const handleProcessBatch = async () => {
    if (!isFormValid) return;

    try {
      setIsProcessing(true);
      setUploadProgress(0);
      setUploadStageText(`Transfiriendo ${queuedFiles.length} archivo(s) al servidor...`);
      sileoToast.info({
        title: 'Iniciando ingestión de lote',
        description: `Subiendo ${queuedFiles.length} archivo(s) con reconocimiento multi-gestión...`,
      });

      const payload = queuedFiles.map((it) => ({
        file: it.file,
        sourceType: it.sourceType,
        tipoEscala: isAcademicSourceType(it.sourceType) ? it.tipoEscala : null,
      }));

      const uploadRes = await dataopsApi.uploadBatch(
        payload,
        (pct) => {
          setUploadProgress(pct);
          if (pct < 100) {
            setUploadStageText(`Subiendo archivos al servidor: ${pct}% completado...`);
          } else {
            setUploadStageText('Archivos transferidos. El servidor está procesando el lote (normalización, fechas y pre-etiquetado)...');
            // La transferencia terminó, la ingesta no: el panel global sigue el avance aunque se cambie de página
            avisarTareaIniciada();
            sileoToast.info({
              title: 'Archivos transferidos al servidor',
              description: 'La ingesta sigue en el servidor. Puedes cambiar de página: te avisaremos al terminar.',
            });
          }
        },
        {
          institucion,
          periodo: 'Auto'
        }
      );

      const perFileResults = uploadRes?.archivos_procesados || uploadRes?.resultados || [];
      const loteId = uploadRes?.id_lote || uploadRes?.doc_ids?.[0];

      if (loteId) {
        localStorage.setItem('last_active_batch_id', String(loteId));
        setActiveBatchId(Number(loteId));
        setLastUploadedBatchId(Number(loteId));
        await loadBatchInspection(Number(loteId));
        await loadInitialData();

        setQueuedFiles((prev) =>
          prev.map((it, idx) => {
            const match = perFileResults[idx] || perFileResults.find((r) => r.nombre_archivo === it.file.name);
            return {
              ...it,
              status: 'Pre-etiquetado',
              statusDetail: match?.mensaje || 'Procesado con chips de catálogo',
              diagnostico: match?.diagnostico_estructural,
              chips: match?.chips_catalogo,
            };
          })
        );

        sileoToast.success({
          title: `Lote #${loteId} procesado exitosamente`,
          description: 'Estructura asimétrica aplanada y pre-etiquetada en el Inspector C.',
        });
      }
    } catch (err) {
      console.error('Error al procesar lote:', err);
      const errDetail = err.response?.data?.detail || err.message || 'Error al procesar el lote en el servidor.';
      sileoToast.error({
        title: 'Error en ingesta de lote',
        description: String(errDetail),
      });
    } finally {
      setIsProcessing(false);
      setUploadStageText('');
    }
  };

  // ─── Datos de la Sección B (Tabla de Lote del Dispatcher) ───
  const batchTableItems = queuedFiles.length > 0
    ? queuedFiles.map((q, idx) => ({
        index: idx,
        nombre: q.file.name,
        size: formatFileSize(q.file.size),
        origen: q.originDetected || mapSourceToOriginCode(q.sourceType, q.file.name),
        filas: q.filasEstimadas || 24,
        fechas: q.fechasReconocidas || 'Por detectar',
        sha256Ok: true,
        estado: q.status === 'Pre-etiquetado' ? 'Pre-etiquetado' : 'En cola',
        isQueued: true,
      }))
    : activeBatchData?.registros?.length > 0
    ? [
        {
          index: 0,
          nombre: sourcesHistory.find(s => s.id_lote === activeBatchId)?.name || `Lote_${activeBatchId}.xlsx`,
          size: '48.2 KB',
          origen: activeBatchData.origen_detectado || 'GSHEETS_ACTA_NOTAS',
          filas: activeBatchData.kpis?.filas_leidas || activeBatchData.registros.length,
          fechas: activeBatchData.rango_fechas || 'Por detectar',
          sha256Ok: true,
          estado: 'Pre-etiquetado',
          isQueued: false,
        }
      ]
    : [];

  // ─── Helpers para resolución segura de chips y metadatos ───
  const resolveChip = (chipsData, key, fallback = '') => {
    if (!chipsData) return fallback;
    if (Array.isArray(chipsData)) {
      const item = chipsData.find(
        (c) => c.label?.toLowerCase() === key.toLowerCase() || c.key?.toLowerCase() === key.toLowerCase()
      );
      return item?.value || item?.val || fallback;
    }
    if (typeof chipsData === 'object') {
      return (
        chipsData[key.toLowerCase()] ||
        chipsData[key.toUpperCase()] ||
        chipsData[key] ||
        fallback
      );
    }
    return fallback;
  };

  const formatMergedCell = (c) => {
    if (!c) return '—';
    if (typeof c === 'object') {
      return c.valor ? `${c.rango} -> "${c.valor}"` : c.rango || '—';
    }
    return String(c);
  };

  // ─── Datos de la Sección C (Inspector de Aplanamiento Asimétrico y Chips) ───
  const currentSelectedFile = batchTableItems[selectedInspectionIndex] || batchTableItems[0] || null;

  // Diagnóstico estructural extraído del archivo real o del lote en base de datos
  const selectedQueuedFile = queuedFiles[selectedInspectionIndex];
  const activeDiag = selectedQueuedFile?.diagnostico || activeBatchData?.diagnostico_estructural || null;

  // Chips resueltos del catálogo institucional
  const activeChips = selectedQueuedFile?.chips || activeBatchData?.chips_catalogo || null;

  // Registros pre-etiquetados reales de staging_registros_crudos
  const filteredRecords = (activeBatchData?.registros || []).filter((r) => {
    if (!currentSelectedFile?.nombre) return true;
    return !r.nombre_archivo || r.nombre_archivo === currentSelectedFile.nombre;
  });
  const activeRecords = (filteredRecords.length > 0 ? filteredRecords : activeBatchData?.registros || []).slice(0, 4);

  return (
    <BatchFlowLayout currentStep={1}>
      {/* ─── BANNER / CALLOUT INTERACTIVO TRAS ÉXITO DE CARGA DE LOTE ─── */}
      {lastUploadedBatchId && (
        <div
          className="floating-artifact"
          style={{
            marginBottom: '20px',
            padding: '14px 18px',
            backgroundColor: 'rgba(27, 135, 84, 0.08)',
            border: '1px solid rgba(27, 135, 84, 0.3)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              backgroundColor: 'rgba(27, 135, 84, 0.15)', color: '#1B8754',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
            }}>
              <CheckCircle2 size={18} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
                ¡Lote #{lastUploadedBatchId} cargado y pre-procesado con éxito!
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                Los archivos fueron validados y el texto crudo aplanado está listo para revisión de texto plano.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              onClick={() => navigate(`/dataops/lote/${lastUploadedBatchId}/texto`)}
              className="btn-pill-gold"
              style={{ fontSize: '12px', padding: '6px 14px' }}
            >
              <span>Pasar a Texto Plano ②</span>
              <ArrowRight size={14} />
            </button>
            <button
              type="button"
              onClick={() => setLastUploadedBatchId(null)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-slate-gray)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center'
              }}
              title="Cerrar notificación"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ─── SECCIÓN A: ZONA DE CARGA MULTIFUENTE Y CONFIGURACIÓN DE LOTE ─── */}
      <div className="dataops-section-a" style={{ marginBottom: '28px' }}>
        
        {/* Panel Izquierdo: Dropzone Multifichero (1 a N archivos) */}
        <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
                Zona de Carga Multifuente (1 a N archivos)
              </h2>
              <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
                Formatos soportados: <strong>Exportaciones Moodle, Google Sheets</strong> (Actas Notas/Asistencia), <strong>Google Forms</strong> (Admisiones/Pagos). Máx. {MAX_TAMANO_ARCHIVO_MB} MB.
              </p>
            </div>
            {queuedFiles.length > 0 && (
              <button
                onClick={() => setQueuedFiles([])}
                className="sileo-btn"
                style={{
                  padding: '5px 12px', fontSize: '11px', borderRadius: '6px',
                  backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                  color: 'var(--color-slate-gray)', cursor: 'pointer', fontWeight: 600
                }}
              >
                Vaciar cola ({queuedFiles.length})
              </button>
            )}
          </div>

          {/* Badges de orígenes admitidos en colores sobrios */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            <span className="chip-cat chip-origen">
              Moodle Export (.csv / .xlsx)
            </span>
            <span className="chip-cat chip-origen">
              Google Sheets (Actas Notas / Asist)
            </span>
            <span className="chip-cat chip-origen">
              Google Forms (Admisiones / Pagos)
            </span>
          </div>

          {/* Dropzone interactivo */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            style={{
              border: isDragging ? '2px dashed var(--color-gira-gold, #D99B26)' : '2px dashed var(--color-border)',
              backgroundColor: isDragging ? 'var(--dataops-gold-bg, rgba(217, 155, 38, 0.08))' : 'var(--color-mist-gray)',
              borderRadius: '12px',
              padding: '24px 20px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onClick={() => document.getElementById('file-upload-input').click()}
          >
            <input
              id="file-upload-input"
              type="file"
              multiple
              accept=".xlsx,.csv"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              backgroundColor: 'rgba(217, 155, 38, 0.12)', color: 'var(--color-gira-gold, #D99B26)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <UploadCloud size={22} />
            </div>

            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-ink-black)', fontFamily: 'var(--font-sohne)' }}>
              Arrastra archivos .XLSX o .CSV aquí
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
              o haz click para seleccionar archivos desde tu equipo
            </div>
          </div>

          {/* Lista de archivos en cola */}
          {queuedFiles.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
              {queuedFiles.map((item) => {
                const isAcademic = isAcademicSourceType(item.sourceType);
                const needsSource = !item.sourceType;

                return (
                  <div
                    key={item.uid}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: needsSource ? '1.5px solid var(--color-gira-gold, #D99B26)' : '1px solid var(--color-border)',
                      backgroundColor: 'var(--color-paper-white)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                        <FileSpreadsheet size={15} color="var(--color-gira-gold, #D99B26)" style={{ flexShrink: 0 }} />
                        <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-ink-black)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.file.name}
                        </span>
                        <span style={{ fontSize: '10.5px', color: 'var(--color-ash-gray)', flexShrink: 0 }}>
                          ({formatFileSize(item.file.size)})
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="chip-cat chip-origen" style={{ fontSize: '10px' }}>
                          {item.originDetected}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(item.uid)}
                          style={{ background: 'none', border: 'none', color: 'var(--color-ash-gray)', cursor: 'pointer', padding: '2px' }}
                          title="Quitar archivo"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>

                    {/* Selector de Tipo Documental si se requiere */}
                    <div style={{ display: 'grid', gridTemplateColumns: isAcademic ? '1fr 1fr' : '1fr', gap: '8px' }}>
                      <div>
                        <select
                          value={item.sourceType}
                          onChange={(e) => handleChangeFileSourceType(item.uid, e.target.value)}
                          className="dataops-select"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                        >
                          <option value="">{UNRECOGNIZED_SOURCE_LABEL}</option>
                          {TIPOS_FUENTE_DATAOPS.map((tf) => (
                            <option key={tf.code} value={tf.code}>
                              {tf.label} ({tf.code})
                            </option>
                          ))}
                        </select>
                      </div>
                      {isAcademic && (
                        <div>
                          <select
                            value={item.tipoEscala || 'CENTESIMAL_100'}
                            onChange={(e) => {
                              const val = e.target.value;
                              setQueuedFiles(prev => prev.map(f => f.uid === item.uid ? { ...f, tipoEscala: val } : f));
                            }}
                            className="dataops-select"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                          >
                            {ESCALAS_ACADEMICAS.map((esc) => (
                              <option key={esc.value} value={esc.value}>
                                {esc.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Panel Derecho: Parámetros del Lote */}
        <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
              Parámetros del Lote
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
              Configuración de periodo destino, umbral de inferencia y protocolo de anonimización.
            </p>
          </div>

          {/* 1. Reconocimiento Temporal Multi-Semestre (Sin selector rígido) */}
          <div style={{
            padding: '12px 14px',
            borderRadius: '10px',
            backgroundColor: 'var(--color-mist-gray)',
            border: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
          }}>
            <Calendar size={18} color="var(--color-gira-gold, #D99B26)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>Reconocimiento Temporal:</span>
                <span className="chip-cat chip-fecha">Automático en archivo</span>
              </div>
              <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '3px 0 0 0', lineHeight: 1.4 }}>
                Inferencia multi-semestre directa desde columnas de fecha y cabeceras sin forzar un periodo fijo.
              </p>
            </div>
          </div>

          {/* 2. Umbral Confianza IA: [85%] */}
          <div style={{
            padding: '12px 14px',
            borderRadius: '10px',
            backgroundColor: 'var(--color-paper-white)',
            border: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sliders size={14} color="var(--color-gira-gold, #D99B26)" /> Umbral Confianza IA
              </label>
              <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--color-gira-gold, #D99B26)', fontFamily: 'var(--font-mono)' }}>
                [{umbralConfianzaIa}%]
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="100"
              value={umbralConfianzaIa}
              onChange={(e) => setUmbralConfianzaIa(Number(e.target.value))}
              style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-gira-gold, #D99B26)' }}
            />
            <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
              Filtro probabilístico para el pre-etiquetado de entidades canónicas de BETO.
            </div>
          </div>

          {/* 3. [x] Anonimización Activa (SHA-256) */}
          <label style={{
            padding: '12px 14px',
            borderRadius: '10px',
            backgroundColor: 'var(--color-paper-white)',
            border: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={anonimizacionActiva}
              onChange={(e) => setAnonimizacionActiva(e.target.checked)}
              style={{ marginTop: '3px', cursor: 'pointer', accentColor: '#1B8754' }}
            />
            <div>
              <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldCheck size={15} color="#1B8754" /> Anonimización Activa (SHA-256)
              </div>
              <p style={{ fontSize: '11px', color: 'var(--color-slate-gray)', margin: '2px 0 0 0', lineHeight: 1.35 }}>
                Protección estricta Cero PII: hashing unidireccional SHA-256 de Cédulas de Identidad y nombres.
              </p>
            </div>
          </label>

          {/* Barra de Progreso Activa durante la Ingesta */}
          {isProcessing && (
            <div style={{
              marginTop: 'auto',
              marginBottom: '10px',
              padding: '12px 14px',
              borderRadius: '8px',
              backgroundColor: 'rgba(217, 155, 38, 0.08)',
              border: '1px solid rgba(217, 155, 38, 0.3)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <RefreshCw size={13} className="animate-spin" color="var(--color-gira-gold, #D99B26)" />
                  {uploadProgress < 100 ? 'Subiendo archivos...' : 'Procesando en servidor...'}
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-gira-gold, #D99B26)' }}>
                  {uploadProgress}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                borderRadius: '4px',
                backgroundColor: 'rgba(0,0,0,0.08)',
                overflow: 'hidden',
                position: 'relative',
              }}>
                <div style={{
                  width: `${Math.max(5, uploadProgress)}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #D99B26 0%, #1B8754 100%)',
                  borderRadius: '4px',
                  transition: 'width 0.3s ease-in-out',
                }} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--color-slate-gray)', margin: '6px 0 0 0', lineHeight: 1.3 }}>
                {uploadStageText || (uploadProgress < 100 ? `Cargando lote: ${uploadProgress}%` : 'Ejecutando pipeline y diagnósticos estructurales...')}
              </p>
            </div>
          )}

          {/* Botón de Procesamiento Principal (Gold Pill) */}
          <button
            onClick={handleProcessBatch}
            disabled={!isFormValid || isProcessing}
            className="btn-pill-gold"
            style={{
              marginTop: isProcessing ? '0' : 'auto',
              padding: '12px 18px',
              fontSize: '13.5px',
            }}
          >
            {isProcessing ? (
              <>
                <RefreshCw size={16} className="animate-spin" /> {uploadProgress < 100 ? `Subiendo Lote (${uploadProgress}%)...` : 'Procesando en Servidor...'}
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" /> Procesar Lote e Inspeccionar Estructura ({queuedFiles.length})
              </>
            )}
          </button>
        </div>
      </div>

      {/* ─── SECCIÓN B: COLA DEL DISPATCHER Y ESTADO DE PREPROCESAMIENTO (Tabla de Lote) ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="var(--color-gira-gold, #D99B26)" /> SECCIÓN B: COLA DEL DISPATCHER Y ESTADO DE PREPROCESAMIENTO
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Inspección heurística de cabeceras, clasificación de origen y validación de anonimización criptográfica.
            </p>
          </div>
          {batchTableItems.length > 0 && (
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              Mostrando <strong>{batchTableItems.length}</strong> archivo(s) en cola / lote activo
            </span>
          )}
        </div>

        {batchTableItems.length === 0 ? (
          <div style={{ padding: '36px', textAlign: 'center', backgroundColor: 'var(--color-mist-gray)', borderRadius: '10px', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            No hay archivos en la cola. Arrastra archivos en la Sección A o selecciona un lote del historial para inspeccionar.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table className="dataops-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Archivo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Origen Detectado (dim_origen)</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Filas</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Anonimización</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Estado</th>
                  <th style={{ padding: '10px 14px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>Inspección</th>
                </tr>
              </thead>
              <tbody>
                {batchTableItems.map((item, idx) => {
                  const isSelected = selectedInspectionIndex === idx;
                  return (
                    <tr
                      key={idx}
                      onClick={() => setSelectedInspectionIndex(idx)}
                      className={`dataops-table-row ${isSelected ? 'selected' : ''}`}
                      style={{ borderBottom: '1px solid var(--color-border)' }}
                    >
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileSpreadsheet size={15} color="var(--color-gira-gold, #D99B26)" />
                          <span>{item.nombre}</span>
                          <span style={{ fontSize: '10.5px', color: 'var(--color-ash-gray)' }}>({item.size})</span>
                        </div>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span className="chip-cat chip-origen" style={{ fontWeight: 700 }}>
                          {item.origen}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                        {item.filas}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: '4px',
                          fontSize: '11px', fontWeight: 700, color: '#1B8754',
                          backgroundColor: 'rgba(27, 135, 84, 0.1)', padding: '2px 8px', borderRadius: '4px'
                        }}>
                          <CheckCircle2 size={12} /> SHA-256 OK
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span className="chip-cat chip-fecha">
                          [{item.estado}]
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                        <button
                          type="button"
                          className="sileo-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedInspectionIndex(idx);
                          }}
                          style={{
                            padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                            backgroundColor: isSelected ? 'var(--color-gira-gold, #D99B26)' : 'var(--color-mist-gray)',
                            color: isSelected ? '#ffffff' : 'var(--color-slate-gray)',
                            border: '1px solid var(--color-border)',
                            cursor: 'pointer',
                            fontWeight: isSelected ? 700 : 500
                          }}
                        >
                          {isSelected ? '✓ Seleccionado' : 'Ver en C'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ─── SECCIÓN C: INSPECTOR DE APLANAMIENTO ASIMÉTRICO Y PRE-ETIQUETADO CON CATÁLOGO (SPLIT VIEW) ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="var(--color-gira-gold, #D99B26)" /> SECCIÓN C: INSPECTOR DE APLANAMIENTO ASIMÉTRICO Y PRE-ETIQUETADO CON CATÁLOGO
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Archivo bajo inspección: <strong>{currentSelectedFile?.nombre || 'Seleccione un archivo en la Sección B'}</strong>
            </p>
          </div>
          {currentSelectedFile && (
            <div style={{ display: 'flex', gap: '6px' }}>
              <span className="chip-cat chip-origen">
                {currentSelectedFile?.origen || 'GSHEETS_ACTA_NOTAS'}
              </span>
              <span className="chip-cat chip-fecha">
                {currentSelectedFile?.fechas || 'Por detectar'}
              </span>
            </div>
          )}
        </div>

        <div className="dataops-split-view">
          
          {/* ── Mitad Izquierda: ESTRUCTURA ORIGINAL DETECTADA (Mini-Grid) ── */}
          <div style={{
            backgroundColor: 'var(--color-mist-gray)',
            border: '1px solid var(--color-border)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--color-gira-gold, #D99B26)' }}>
                Estructura Original Detectada (Mini-Grid)
              </span>
              {activeDiag && (
                <span style={{ fontSize: '10.5px', color: 'var(--color-slate-gray)', fontFamily: 'var(--font-mono)' }}>
                  Fila de Cabecera: #{activeDiag.fila_cabecera_desplazada || activeDiag.fila_cabecera || 5}
                </span>
              )}
            </div>

            {activeDiag ? (
              <>
                {/* Diagnóstico de celdas combinadas y cabecera desplazada */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11.5px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-ink-black)' }}>
                    <span style={{ fontWeight: 700, color: 'var(--color-gira-gold, #D99B26)' }}>Celda combinada:</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>
                      {formatMergedCell(activeDiag.celdas_combinadas?.[0])}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-ink-black)' }}>
                    <span style={{ fontWeight: 700, color: 'var(--color-ink-black)' }}>Cabecera desplazada:</span>
                    <span>Fila #{activeDiag.fila_cabecera_desplazada || activeDiag.fila_cabecera || 5} detectada y normalizada</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-ink-black)' }}>
                    <span style={{ fontWeight: 700, color: 'var(--color-slate-gray)' }}>Columnas dinámicas:</span>
                    <span>{activeDiag.columnas_dinamicas ? activeDiag.columnas_dinamicas.join(', ') : 'Nota1, NotaFinal, %Asist'}</span>
                  </div>
                </div>

                {/* Advertencias estructurales */}
                <div style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(217, 155, 38, 0.08)',
                  border: '1px solid rgba(217, 155, 38, 0.25)',
                  fontSize: '11.5px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}>
                  <div style={{ fontWeight: 700, color: 'var(--color-gira-gold, #D99B26)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={13} /> Advertencias estructurales resueltas:
                  </div>
                  {Array.isArray(activeDiag.advertencias_estructurales) && activeDiag.advertencias_estructurales.length > 0 ? (
                    activeDiag.advertencias_estructurales.map((adv, aIdx) => (
                      <div key={aIdx} style={{ color: 'var(--color-slate-gray)', paddingLeft: '18px' }}>
                        • {adv}
                      </div>
                    ))
                  ) : (
                    <>
                      <div style={{ color: 'var(--color-slate-gray)', paddingLeft: '18px' }}>
                        • {activeDiag.encabezados_multinivel_aplanados || 3} encabezados multinivel aplanados automáticamente.
                      </div>
                      <div style={{ color: 'var(--color-slate-gray)', paddingLeft: '18px' }}>
                        • {activeDiag.filas_subtotales_descartadas || 2} filas de subtotales/firmas descartadas.
                      </div>
                    </>
                  )}
                </div>

                {/* Mini-Grid Visual */}
                {Array.isArray(activeDiag.mini_grid) && activeDiag.mini_grid.length > 0 ? (
                  <div className="mini-grid-container">
                    <table className="mini-grid-table">
                      <tbody>
                        {activeDiag.mini_grid.map((row, rIdx) => {
                          const isMergedRow = rIdx === 0;
                          const headerIdx = (activeDiag.fila_cabecera_desplazada || activeDiag.fila_cabecera || 5) - 1;
                          const isHeaderRow = rIdx === headerIdx;
                          return (
                            <tr key={rIdx}>
                              {(Array.isArray(row) ? row : []).map((cellVal, cIdx) => {
                                const isObj = typeof cellVal === 'object' && cellVal !== null;
                                const cellText = isObj ? (cellVal.valor ?? '') : String(cellVal ?? '');
                                const isCellMerged = isObj ? Boolean(cellVal.es_combinada) : isMergedRow;
                                const isCellHeader = isObj ? Boolean(cellVal.es_cabecera) : isHeaderRow;
                                const cellCoord = isObj && cellVal.coord
                                  ? `[${cellVal.coord}]`
                                  : `[${String.fromCharCode(65 + cIdx)}${rIdx + 1}]`;

                                let cellClass = '';
                                if (isCellMerged) cellClass = 'mini-grid-cell-merged';
                                else if (isCellHeader) cellClass = 'mini-grid-cell-header';

                                return (
                                  <td
                                    key={cIdx}
                                    className={cellClass}
                                    title={isObj && cellVal.rango ? `Rango combinado: ${cellVal.rango}` : undefined}
                                  >
                                    <span className="mini-grid-coord">{cellCoord}</span>
                                    {cellText || '—'}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </>
            ) : (
              <div style={{
                padding: '36px 16px',
                textAlign: 'center',
                backgroundColor: 'var(--color-paper-white)',
                borderRadius: '8px',
                border: '1px dashed var(--color-border)',
                color: 'var(--color-slate-gray)',
                fontSize: '12px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FileSpreadsheet size={28} color="var(--color-gira-gold, #D99B26)" />
                <span style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>Sin estructura tabular cargada</span>
                <span style={{ maxWidth: '300px' }}>Arrastra un archivo en la Sección A o selecciona un lote para visualizar el mini-grid de cabeceras.</span>
              </div>
            )}
          </div>

          {/* ── Mitad Derecha: TEXTO PLANO ESTRUCTURADO Y PRE-ETIQUETADO ── */}
          <div style={{
            backgroundColor: 'var(--color-paper-white)',
            border: '1px solid var(--color-border)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#1B8754' }}>
                Texto Plano Estructurado y Pre-etiquetado
              </span>
              <span style={{ fontSize: '10.5px', color: 'var(--color-slate-gray)' }}>
                Catálogo Maestro: {totalProgramas ?? '—'} Prog. Activos
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '340px', overflowY: 'auto' }}>
              {activeRecords.length > 0 ? (
                activeRecords.map((rec, rIdx) => (
                  <div
                    key={rIdx}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--color-mist-gray)',
                      border: '1px solid var(--color-border)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: 'var(--color-ink-black)', fontFamily: 'var(--font-mono)' }}>
                        [REG_{String(rIdx + 1).padStart(3, '0')}] ORIGEN: {rec.origen_detectado || rec.origen || currentSelectedFile?.origen || 'GSHEETS_ACTA_ASIST'}
                      </span>
                    </div>

                    {/* Chips resueltos del catálogo */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="chip-cat chip-programa">
                        PROGRAMA_CAT: {resolveChip(rec.chips || activeChips, 'programa_cat', rec.programa || 'No asignado')}
                      </span>
                      <span className="chip-cat chip-modulo">
                        MODULO_CAT: {resolveChip(rec.chips || activeChips, 'modulo_cat', rec.modulo || 'No asignado')}
                      </span>
                      <span className="chip-cat chip-precio">
                        PRECIO_BASE_CAT: {resolveChip(rec.chips || activeChips, 'precio_base_cat', '—')}
                      </span>
                      <span className="chip-cat chip-fecha">
                        FECHA: {resolveChip(rec.chips || activeChips, 'fecha_detectada', currentSelectedFile?.fechas || 'Auto')}
                      </span>
                    </div>

                    {/* Oración canónica para BETO */}
                    <div style={{
                      padding: '6px 8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--color-paper-white)',
                      border: '1px solid var(--color-border)',
                      fontSize: '11.5px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--color-ink-black)',
                      lineHeight: 1.4
                    }}>
                      TEXTO_CRUDO: "{rec.texto_crudo || rec.oracion_beto || rec.texto_plano || '—'}"
                    </div>
                  </div>
                ))
              ) : (
                <div style={{
                  padding: '36px 16px',
                  textAlign: 'center',
                  backgroundColor: 'var(--color-mist-gray)',
                  borderRadius: '8px',
                  border: '1px dashed var(--color-border)',
                  color: 'var(--color-slate-gray)',
                  fontSize: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <FileText size={28} color="var(--color-gira-gold, #D99B26)" />
                  <span style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>Sin oraciones canónicas pre-etiquetadas</span>
                  <span style={{ maxWidth: '300px' }}>Arrastre archivos .xlsx o .csv en la Sección A o seleccione un lote del historial para inspeccionar oraciones.</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Barra de Acciones de Pie de la Sección C */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '20px',
          paddingTop: '16px',
          borderTop: '1px solid var(--color-border)',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <button
            type="button"
            onClick={() => {
              setQueuedFiles([]);
              setActiveBatchData(null);
              setLastUploadedBatchId(null);
              sileoToast.info({ title: 'Lote cancelado', description: 'Se vació la cola y la inspección del lote activo.' });
            }}
            className="btn-pill-secondary"
          >
            Cancelar Lote
          </button>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => {
                const targetId = activeBatchId || localStorage.getItem('last_active_batch_id');
                if (targetId) {
                  navigate(`/dataops/lote/${targetId}/beto`);
                } else {
                  sileoToast.warning({
                    title: 'Procese un lote primero',
                    description: 'Debe cargar y procesar un lote antes de ejecutar la extracción NER con BETO.'
                  });
                }
              }}
              className="btn-pill-secondary"
              title="Atajo directo al análisis con BETO"
            >
              <Sparkles size={14} color="var(--color-gira-gold, #D99B26)" />
              <span>Ejecutar BETO Directo ③</span>
            </button>

            <button
              type="button"
              onClick={() => {
                const targetId = activeBatchId || localStorage.getItem('last_active_batch_id');
                if (targetId) {
                  navigate(`/dataops/lote/${targetId}/texto`);
                } else {
                  sileoToast.warning({
                    title: 'Procese un lote primero',
                    description: 'Debe cargar y procesar un lote antes de pasar a la revisión de texto plano.'
                  });
                }
              }}
              className="btn-pill-gold"
            >
              <span>Pasar a Texto Plano ②</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* ─── ACORDEÓN INFERIOR: HISTORIAL DE LOTES PROCESADOS ─── */}
      <div className="floating-artifact" style={{ padding: '20px 24px' }}>
        <button
          type="button"
          onClick={() => setHistoryExpanded(prev => !prev)}
          style={{
            width: '100%',
            background: 'none',
            border: 'none',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            padding: 0,
            textAlign: 'left'
          }}
        >
          <div>
            <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Historial de Lotes Procesados ({sourcesHistory.length})</span>
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '3px 0 0 0' }}>
              Registro cronológico de lotes, orígenes y bitácoras técnicas (.MD)
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            <span>{historyExpanded ? 'Ocultar' : 'Mostrar'}</span>
            {historyExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </button>

        {historyExpanded && (
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px', gap: '8px' }}>
              <button
                type="button"
                onClick={() => handleOpenTelemetry(sourcesHistory[0] || { id: 1, nombre_archivo: 'Lote Reciente' })}
                className="sileo-btn"
                style={{
                  padding: '5px 12px', fontSize: '11px',
                  backgroundColor: '#0C1E33', color: '#FAF9F6', border: '1px solid var(--color-border)',
                  borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600
                }}
              >
                <Terminal size={12} color="var(--color-gira-gold, #D99B26)" /> 📋 Bitácora Técnica (.MD)
              </button>
              <button
                type="button"
                onClick={loadInitialData}
                className="sileo-btn"
                style={{
                  padding: '5px 12px', fontSize: '11px',
                  backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                  borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <RefreshCw size={12} /> Actualizar
              </button>
            </div>

            {isLoadingHistory ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '12.5px' }}>
                Cargando historial...
              </div>
            ) : sourcesHistory.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '12.5px' }}>
                No se registraron lotes previos.
              </div>
            ) : (
              <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                      <th style={{ padding: '8px 12px', color: 'var(--color-slate-gray)' }}>Lote / Archivo</th>
                      <th style={{ padding: '8px 12px', color: 'var(--color-slate-gray)' }}>Origen</th>
                      <th style={{ padding: '8px 12px', color: 'var(--color-slate-gray)' }}>Registros</th>
                      <th style={{ padding: '8px 12px', color: 'var(--color-slate-gray)' }}>Fecha Carga</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-slate-gray)' }}>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourcesHistory.map((src) => {
                      const navId = src.id_lote || src.id || src.id_documento;
                      const fileName = src.nombre_archivo || src.name || `Documento_${navId}`;
                      const sourceType = src.tipo_fuente || src.tipo_documento || 'ACTA';
                      const recordCount = src.registros_detectados ?? src.total_registros ?? src.records ?? 0;
                      const dateDisplay = src.fecha_carga ? new Date(src.fecha_carga).toLocaleDateString() : (src.date || 'Reciente');
                      return (
                        <tr key={src.id || src.id_documento} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                            {src.id_lote ? <span style={{ color: 'var(--color-gira-gold, #D99B26)', fontFamily: 'var(--font-mono)', marginRight: '6px' }}>[Lote #{src.id_lote}]</span> : null}
                            {fileName}
                          </td>
                          <td style={{ padding: '8px 12px', color: 'var(--color-slate-gray)' }}>{sourceType}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>{recordCount}</td>
                          <td style={{ padding: '8px 12px', color: 'var(--color-ash-gray)' }}>{dateDisplay}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px', justifyContent: 'flex-end' }}>
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveBatchId(Number(navId));
                                  loadBatchInspection(Number(navId));
                                  setHistoryExpanded(false);
                                }}
                                className="sileo-btn"
                                style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '4px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', cursor: 'pointer' }}
                              >
                                Cargar en Vista 1
                              </button>
                              <button
                                type="button"
                                onClick={() => navigate(`/dataops/lote/${navId}/texto`)}
                                className="sileo-btn"
                                style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '4px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', cursor: 'pointer' }}
                              >
                                ② Texto
                              </button>
                              <button
                                type="button"
                                onClick={() => navigate(`/dataops/lote/${navId}/beto`)}
                                className="sileo-btn"
                                style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '4px', backgroundColor: 'var(--color-gira-gold, #D99B26)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600 }}
                              >
                                ③ BETO
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ─── DRAWER DE BITÁCORA TÉCNICA Y REPORTE MARKDOWN (.MD) ─── */}
      <PipelineTelemetryDrawer
        isOpen={telemetryOpen}
        onClose={() => setTelemetryOpen(false)}
        logs={telemetryLogs}
        onClearLogs={() => setTelemetryLogs([])}
        isProcessing={isProcessing}
        lotName={(telemetryDoc?.nombre_archivo || telemetryDoc?.name) ? `Archivo: ${telemetryDoc.nombre_archivo || telemetryDoc.name}` : 'Lote Activo'}
        sources={sourcesHistory}
        activeDocId={telemetryDoc?.id_documento || telemetryDoc?.id || 1}
        markdownReport={telemetryMarkdown}
        summaryMetrics={telemetryMetrics}
      />
    </BatchFlowLayout>
  );
}
