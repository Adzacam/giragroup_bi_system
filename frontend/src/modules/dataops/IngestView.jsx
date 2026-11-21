import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud, FileSpreadsheet, Play,
  Eye, RefreshCw, Trash2,
  Calendar, ShieldCheck
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import BatchHistory from './components/BatchHistory';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import usePaginacion from '../../hooks/usePaginacion';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { clearLoteFlowSession } from './context/LoteFlowContext';
import useTextoPreparado from './hooks/useTextoPreparado';
import useResumenPreparacion from './hooks/useResumenPreparacion';
import AnimatedNumberV2 from '../../v2/motion/AnimatedNumberV2';
import { dataopsApi } from '../../api/dataopsApi';
import { mensajeError } from '../../utils/mensajeError';
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
  UMBRAL_INDICE_REGISTRO,
  getTipoFuenteLabel,
} from '../../constants/dataopsConfig';
import {
  getSelectedQueueFiles,
  isAllQueueSelected,
  toggleSelectAllQueue,
  toggleUidSelection,
  validateQueueSelection,
} from './utils/cargaHistorialHelpers';

export default function IngestView() {

  // ─── Estado de la cola multi-archivo (zona de carga) ───
  const [queuedFiles, setQueuedFiles] = useState([]);
  const [selectedQueueUids, setSelectedQueueUids] = useState([]);
  const [expandedDetailKey, setExpandedDetailKey] = useState(null);
  const institucion = 'GiraGroup Posgrado';
  const processingRef = useRef(false);
  const dropzoneRef = useRef(null);
  const queueCheckRef = useRef(false);
  const [isCheckingFiles, setIsCheckingFiles] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(null);

  // ─── Estados de Proceso e Historial ───
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStageText, setUploadStageText] = useState('');

  // ─── Estado de Lote Activo para inspección desde historial ───
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [activeBatchData, setActiveBatchData] = useState(null);
  const [isLoadingBatchData, setIsLoadingBatchData] = useState(false);

  // ─── Estados del Drawer de Bitácora Técnica y Reporte Markdown (.MD) ───
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [telemetryDoc, setTelemetryDoc] = useState(null);

  // ─── Vista previa por hoja y mapeo editable (FU-L8) ───
  const [workbookPreviews, setWorkbookPreviews] = useState({});
  const [loadingPreviewUid, setLoadingPreviewUid] = useState(null);

  const handleTogglePreview = async (item) => {
    if (expandedDetailKey === item.uid) {
      setExpandedDetailKey(null);
      return;
    }
    setExpandedDetailKey(item.uid);
    if (workbookPreviews[item.uid] || loadingPreviewUid === item.uid) return;
    setLoadingPreviewUid(item.uid);
    try {
      const prev = await dataopsApi.previewWorkbook(item.file, item.sourceType || null);
      setWorkbookPreviews((curr) => ({ ...curr, [item.uid]: prev }));
    } catch (err) {
      sileoToast.error({ title: 'No se pudo generar la vista previa', description: mensajeError(err) });
    } finally {
      setLoadingPreviewUid(null);
    }
  };

  const handleChangeColumnMapping = (uid, columnaOrigen, nuevoCampo) => {
    setWorkbookPreviews((curr) => {
      const prev = curr[uid];
      if (!prev) return curr;
      return {
        ...curr,
        [uid]: {
          ...prev,
          mapeo_columnas: (prev.mapeo_columnas || []).map((m) =>
            m.columna_origen === columnaOrigen ? { ...m, campo_canonico: nuevoCampo } : m
          ),
        },
      };
    });
  };

  const loadInitialData = async () => {
    try {
      const lastId = localStorage.getItem('last_active_batch_id');
      let reanudable = !!lastId;
      if (reanudable) {
        // Un lote ya consolidado cierra el flujo: Ingesta arranca en blanco para cargar archivos nuevos
        try {
          const ctx = await dataopsApi.getLoteContext(lastId);
          if (String(ctx?.id_lote) !== String(lastId) || ctx?.estado_flujo === 'CONSOLIDADO') reanudable = false;
        } catch { reanudable = false; }
      }
      if (reanudable) {
        setActiveBatchId(Number(lastId));
        await loadBatchInspection(Number(lastId));
      } else {
        localStorage.removeItem('last_active_batch_id');
        setActiveBatchId(null);
        setActiveBatchData(null);
      }
    } catch (err) {
      sileoToast.error({ title: 'No se pudo recuperar el lote', description: 'Selecciona un lote del historial para continuar.' });
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadBatchInspection = async (batchId) => {
    if (!batchId) return;
    try {
      setIsLoadingBatchData(true);
      setActiveBatchData(null);
      const batchRes = await dataopsApi.getLoteContext(batchId);
      if (batchRes && batchRes.archivos) {
        setActiveBatchData(batchRes);
      }
    } catch (err) {
      sileoToast.error({ title: 'No se pudo cargar la vista previa', description: 'Selecciona de nuevo el lote para reintentarlo.' });
    } finally {
      setIsLoadingBatchData(false);
    }
  };

  const handleOpenTelemetry = async (src) => {
    const docId = src?.id_documento;
    if (!docId || loadingLogs) return;
    setLoadingLogs(docId);
    try {
      const res = await dataopsApi.getLogs(docId);
      setTelemetryDoc(res.document_meta);
      queryClient.setQueryData([...DATAOPS_QUERY_KEY, 'bitacora', docId, 1, 1], res);
      setTelemetryOpen(true);
    } catch {
      sileoToast.error({ title: 'No se pudo abrir la bitácora', description: 'Inténtalo de nuevo.' });
    } finally { setLoadingLogs(null); }
  };

  const handleNewBatch = () => {
    if (activeBatchId) clearLoteFlowSession(activeBatchId);
    localStorage.removeItem('last_active_batch_id');
    setActiveBatchId(null);
    setActiveBatchData(null);
    setQueuedFiles([]);
    setSelectedQueueUids([]);
    setExpandedDetailKey(null);
    queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    dropzoneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    dropzoneRef.current?.focus({ preventScroll: true });
  };

  const handleClearQueue = () => {
    if (processingRef.current || queueCheckRef.current) return;
    setQueuedFiles([]);
    setSelectedQueueUids([]);
    setExpandedDetailKey(null);
  };

  const addFilesToQueue = async (fileList) => {
    const incoming = Array.from(fileList || []);
    if (incoming.length === 0 || processingRef.current || queueCheckRef.current) return;

    if (queuedFiles.length + incoming.length > MAX_ARCHIVOS_POR_LOTE) {
      sileoToast.error({
        title: 'Límite de archivos por lote excedido',
        description: `Se permiten máximo ${MAX_ARCHIVOS_POR_LOTE} archivos simultáneos por lote.`,
      });
      return;
    }

    queueCheckRef.current = true;
    setIsCheckingFiles(true);
    try {
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

        validItems.push({
          uid: `${f.name}_${f.size}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          file: f,
          sourceType: canonicalCode,
          tipoEscala: isAcademicSourceType(canonicalCode) ? '' : null,
          status: 'En cola',
        });
      }

      if (validItems.length > 0) {
        setQueuedFiles((prev) => [...prev, ...validItems]);
        setSelectedQueueUids((prev) => [...prev, ...validItems.map((it) => it.uid)]);
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
    } catch {
      sileoToast.error({ title: 'No se pudieron revisar los archivos', description: 'Selecciona los archivos de nuevo.' });
    } finally { queueCheckRef.current = false; setIsCheckingFiles(false); }
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
    if (processingRef.current || queueCheckRef.current) return;
    setQueuedFiles((prev) => prev.filter((item) => item.uid !== uid));
    setSelectedQueueUids((prev) => prev.filter((id) => id !== uid));
    if (expandedDetailKey === uid) setExpandedDetailKey(null);
  };

  const handleChangeFileSourceType = (uid, newCode) => {
    setQueuedFiles((prev) =>
      prev.map((item) => {
        if (item.uid !== uid) return item;
        const academic = isAcademicSourceType(newCode);
        return {
          ...item,
          sourceType: newCode,
          tipoEscala: academic ? (item.tipoEscala || '') : null,
          status: 'En cola',
        };
      })
    );
  };

  // Validaciones de los archivos seleccionados en cola
  const selectedQueueFiles = getSelectedQueueFiles(queuedFiles, selectedQueueUids);
  const allQueueSelected = isAllQueueSelected(queuedFiles, selectedQueueUids);
  const queueValidation = validateQueueSelection(selectedQueueFiles, MAX_ARCHIVOS_POR_LOTE, institucion);
  const isFormValid = queueValidation.valid;

  const handleProcessBatch = async () => {
    if (!isFormValid || processingRef.current || isCheckingFiles) return;
    processingRef.current = true;
    const filesToSend = selectedQueueFiles;

    try {
      setIsProcessing(true);
      setUploadProgress(0);
      setUploadStageText(`Transfiriendo ${filesToSend.length} archivo(s) al servidor...`);
      sileoToast.info({
        title: 'Cargando archivos',
        description: `Se enviarán ${filesToSend.length} archivo(s) para procesar.`,
      });

      const payload = filesToSend.map((it) => ({
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

      const exitosos = uploadRes?.archivos_exitosos ?? 0;
      const fallidos = perFileResults.filter(r => r.status !== 'procesado');
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });

      const resultByUid = new Map();
      filesToSend.forEach((it, idx) => {
        if (perFileResults[idx]) resultByUid.set(it.uid, perFileResults[idx]);
      });

      const processedUids = new Set();
      setQueuedFiles(prev =>
        prev
          .map((it) => {
            const r = resultByUid.get(it.uid);
            if (!r) return it;
            if (r.status === 'procesado') {
              processedUids.add(it.uid);
              return null;
            }
            const backendCode = toCanonicalSourceCode(r.tipo_fuente) || it.sourceType;
            return { ...it, sourceType: backendCode, status: 'Por revisar' };
          })
          .filter(Boolean)
      );
      setSelectedQueueUids((prev) => prev.filter((uid) => !processedUids.has(uid)));

      if (fallidos.length) {
        sileoToast.warning({ title: `${fallidos.length} archivo(s) sin procesar`, description: fallidos.map(r => `${r.nombre_archivo}: ${r.mensaje || 'Revisa el archivo.'}`).join('\n') });
      }
      if (loteId && exitosos > 0) {
        localStorage.setItem('last_active_batch_id', String(loteId));
        setActiveBatchId(Number(loteId));
        await loadBatchInspection(Number(loteId));

        sileoToast.success({
          title: `Lote #${loteId} procesado exitosamente`,
          description: `${exitosos} archivo(s) cargados. Ya puedes revisar su contenido.`,
        });
      }
    } catch (err) {
      console.error('Error al procesar lote:', err);
      sileoToast.error({
        title: 'Error en ingesta de lote',
        description: mensajeError(err, 'No se pudieron procesar los archivos. Inténtalo de nuevo.'),
      });
    } finally {
      processingRef.current = false;
      setIsProcessing(false);
      setUploadStageText('');
    }
  };

  const inspectedFiles = (activeBatchData?.archivos || []).map((a, index) => ({
    key: `lote_${activeBatchId || 'x'}_${a.id_documento || index}`,
    nombre: a.nombre_archivo || 'Sin dato',
    size: 'Sin dato',
    origen: getTipoFuenteLabel(a.tipo_fuente) || a.tipo_fuente || 'Sin dato',
    filas: a.total_registros ?? 'Sin dato',
    fechas: activeBatchData?.rango_fechas || 'Sin dato',
    estado: 'Texto listo',
  }));
  const queuePagination = usePaginacion(queuedFiles);
  const inspectedPagination = usePaginacion(inspectedFiles);
  const { data: prepResumen } = useTextoPreparado(activeBatchId, null, 1, !!activeBatchId && inspectedFiles.length > 0);
  const prepKpis = useResumenPreparacion(prepResumen);

  return (
    <BatchFlowLayout currentStep={1}>
      {/* ─── SECCIÓN A: ZONA DE CARGA MULTIFUENTE Y REGLAS ─── */}
      <div className="dataops-section-a" style={{ marginBottom: '28px' }}>

        {/* Panel Izquierdo: Dropzone Multifichero + Acciones de Cola */}
        <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
              Cargar archivos
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
              Puedes cargar archivos de <strong>Exportaciones Moodle, Google Sheets</strong> (Actas Notas/Asistencia), <strong>Google Forms</strong> (Admisiones/Pagos). Hasta {MAX_ARCHIVOS_POR_LOTE} archivos .xlsx o .csv, de {MAX_TAMANO_ARCHIVO_MB} MB cada uno.
            </p>
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
              border: isDragging ? '2px dashed var(--color-gira-gold)' : '2px dashed var(--color-border)',
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
            role="button"
            ref={dropzoneRef}
            tabIndex={isProcessing || isCheckingFiles ? -1 : 0}
            aria-label="Seleccionar archivos"
            aria-disabled={isProcessing || isCheckingFiles}
            onKeyDown={(e) => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); if (!isProcessing && !isCheckingFiles) document.getElementById('file-upload-input').click(); } }}
            onClick={() => { if (!isProcessing && !isCheckingFiles) document.getElementById('file-upload-input').click(); }}
          >
            <input
              id="file-upload-input"
              type="file"
              multiple
              disabled={isProcessing || isCheckingFiles}
              accept=".xlsx,.csv"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              backgroundColor: 'var(--dataops-gold-bg)', color: 'var(--color-gira-gold)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <UploadCloud size={22} />
            </div>

            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-ink-black)', fontFamily: 'var(--font-sohne)' }}>
              Arrastra archivos .XLSX o .CSV aquí
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
              {isCheckingFiles ? 'Revisando archivos…' : 'o haz clic para seleccionarlos desde tu equipo'}
            </div>
          </div>

          {/* Botones de acción junto a la zona de carga */}
          <div className="dataops-queue-actions">
            <Button
              variant="ghost"
              onClick={handleProcessBatch}
              isLoading={isProcessing}
              loadingText={uploadProgress < 100 ? `Subiendo (${uploadProgress} %)…` : 'Procesando…'}
              disabled={!isFormValid || isCheckingFiles}
              className="btn-pill-gold"
              style={{ padding: '10px 18px', fontSize: '13px' }}
            >
              <Play size={15} fill="currentColor" /> Procesar archivos ({selectedQueueFiles.length})
            </Button>

            <Button
              variant="ghost"
              disabled={queuedFiles.length === 0 || isProcessing || isCheckingFiles}
              onClick={handleClearQueue}
              className="sileo-btn"
              style={{
                padding: '8px 14px', fontSize: '12px', borderRadius: '8px',
                backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                color: 'var(--color-slate-gray)', fontWeight: 600
              }}
            >
              Vaciar cola ({queuedFiles.length})
            </Button>
          </div>
        </div>

        {/* Panel Derecho: Reglas de procesamiento */}
        <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
              Reglas de procesamiento
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
              Las fechas se leen del archivo. La confianza mínima y la protección de datos son fijas.
            </p>
          </div>

          {/* 1. Reconocimiento Temporal Multi-Semestre */}
          <div style={{
            padding: '12px 14px',
            borderRadius: '10px',
            backgroundColor: 'var(--color-mist-gray)',
            border: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
          }}>
            <Calendar size={18} color="var(--color-gira-gold)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>Fechas:</span>
                <span className="chip-cat chip-fecha">Automático en archivo</span>
              </div>
              <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '3px 0 0 0', lineHeight: 1.4 }}>
                Se reconocen las fechas de las columnas y encabezados del archivo.
              </p>
            </div>
          </div>

          <div style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
            <strong style={{ color: 'var(--color-ink-black)', fontSize: '12.5px' }}>{UMBRAL_INDICE_REGISTRO} % fijo</strong>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Es el mínimo de confianza para aceptar un registro directamente. Consulta los rangos en el glosario.</p>
          </div>
          <div style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
            <strong style={{ color: 'var(--color-ink-black)', fontSize: '12.5px' }}><ShieldCheck size={15} /> Datos personales siempre protegidos</strong>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>La protección se aplica en el servidor y no se puede desactivar desde esta pantalla.</p>
          </div>

          {/* Barra de Progreso Activa durante la Ingesta */}
          {isProcessing && (
            <div style={{
              marginTop: 'auto',
              padding: '12px 14px',
              borderRadius: '8px',
              backgroundColor: 'var(--dataops-gold-bg)',
              border: '1px solid var(--dataops-gold-border)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <RefreshCw size={13} className="animate-spin" color="var(--color-gira-gold)" />
                  {uploadProgress < 100 ? 'Subiendo archivos...' : 'Procesando en servidor...'}
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-gira-gold)' }}>
                  {uploadProgress}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                borderRadius: '4px',
                backgroundColor: 'var(--color-border)',
                overflow: 'hidden',
                position: 'relative',
              }}>
                <div style={{
                  width: `${Math.max(5, uploadProgress)}%`,
                  height: '100%',
                  background: 'var(--color-gira-gold)',
                  borderRadius: '4px',
                  transition: 'width 0.3s ease-in-out',
                }} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--color-slate-gray)', margin: '6px 0 0 0', lineHeight: 1.3 }}>
                {uploadStageText || (uploadProgress < 100 ? `Cargando lote: ${uploadProgress}%` : 'Ejecutando pipeline y diagnósticos estructurales...')}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ─── Cola de archivos / Archivos del lote (Tabla con detalle integrado en cada fila) ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }} aria-busy={isLoadingBatchData}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="var(--color-gira-gold)" /> {queuedFiles.length > 0 ? 'Cola de archivos' : 'Archivos del lote'}
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              {queuedFiles.length > 0
                ? 'Selecciona los archivos a procesar, verifica su tipo documental y revisa su detalle en cada fila.'
                : 'Detalle de los archivos del lote inspeccionado.'}
            </p>
          </div>
          {queuedFiles.length > 0 ? (
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              <strong>{selectedQueueFiles.length}</strong> de <strong>{queuedFiles.length}</strong> seleccionado(s)
            </span>
          ) : inspectedFiles.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                Mostrando <strong>{inspectedFiles.length}</strong> archivo(s) del lote #{activeBatchId}
              </span>
              <Button variant="ghost" disabled={isProcessing || isCheckingFiles || isLoadingBatchData} onClick={handleNewBatch}>
                Limpiar vista
              </Button>
            </div>
          ) : null}
        </div>

        {isLoadingBatchData ? (
          <p role="status" style={{ color: 'var(--color-slate-gray)', fontSize: '13px' }}>Cargando información del lote…</p>
        ) : queuedFiles.length > 0 ? (
          <div style={{ overflowX: 'auto', maxWidth: '100%', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table className="dataops-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr>
                  <th style={{ width: 36 }}>
                    <input
                      type="checkbox"
                      aria-label="Seleccionar todo"
                      checked={allQueueSelected}
                      disabled={isProcessing || isCheckingFiles}
                      onChange={() => setSelectedQueueUids((prev) => toggleSelectAllQueue(queuedFiles, prev))}
                    />
                  </th>
                  <th>Archivo</th>
                  <th>Tipo documental</th>
                  <th>Escala</th>
                  <th>Protección</th>
                  <th>Estado</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {queuePagination.visibles.map((item) => {
                  const isSelected = selectedQueueUids.includes(item.uid);
                  const isAcademic = isAcademicSourceType(item.sourceType);
                  const isEvalDocente = toCanonicalSourceCode(item.sourceType) === 'EVALUACION_DOCENTE';
                  const isExpanded = expandedDetailKey === item.uid;
                  const tipoLabel = getTipoFuenteLabel(item.sourceType) || 'Por seleccionar';
                  const fileSize = formatFileSize(item.file.size);

                  return (
                    <React.Fragment key={item.uid}>
                      <tr
                        className={`dataops-table-row ${isSelected ? 'selected' : ''}`}
                        style={{ cursor: 'default' }}
                      >
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Seleccionar ${item.file.name}`}
                            checked={isSelected}
                            disabled={isProcessing || isCheckingFiles}
                            onChange={() => setSelectedQueueUids((prev) => toggleUidSelection(prev, item.uid))}
                          />
                        </td>
                        <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileSpreadsheet size={15} color="var(--color-gira-gold)" style={{ flexShrink: 0 }} />
                            <span>{item.file.name}</span>
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 400, marginTop: '3px' }}>
                            {fileSize} · {tipoLabel} · {item.status}
                          </div>
                        </td>
                        <td>
                          <select
                            aria-label={`Tipo de archivo de ${item.file.name}`}
                            disabled={isProcessing}
                            value={item.sourceType}
                            onChange={(e) => handleChangeFileSourceType(item.uid, e.target.value)}
                            className="dataops-select"
                            style={{ padding: '4px 8px', fontSize: '11.5px', minWidth: '150px' }}
                          >
                            <option value="">{UNRECOGNIZED_SOURCE_LABEL}</option>
                            {TIPOS_FUENTE_DATAOPS.map((tf) => (
                              <option key={tf.code} value={tf.code}>
                                {tf.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          {isAcademic ? (
                            <select
                              value={item.tipoEscala || ''}
                              aria-label={`Escala de notas de ${item.file.name}`}
                              disabled={isProcessing}
                              onChange={(e) => {
                                const val = e.target.value;
                                setQueuedFiles(prev => prev.map(f => f.uid === item.uid ? { ...f, tipoEscala: val } : f));
                              }}
                              className="dataops-select"
                              style={{ padding: '4px 8px', fontSize: '11.5px', minWidth: '150px' }}
                            >
                              <option value="">Selecciona la escala de notas</option>
                              {ESCALAS_ACADEMICAS.map((esc) => (
                                <option key={esc.value} value={esc.value}>
                                  {esc.label}
                                </option>
                              ))}
                            </select>
                          ) : isEvalDocente ? (
                            <div
                              role="note"
                              style={{
                                fontSize: '11px',
                                color: 'var(--color-slate-gray)',
                                padding: '4px 8px',
                                backgroundColor: 'var(--color-mist-gray)',
                                borderRadius: '6px',
                                border: '1px solid var(--color-border)',
                              }}
                            >
                              Escala de respuesta: 1 a 5 / 1 a 10 (detectada)
                            </div>
                          ) : (
                            <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>No aplica</span>
                          )}
                        </td>
                        <td>
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: '4px',
                            fontSize: '11px', fontWeight: 700, color: 'var(--color-alert-green)',
                            backgroundColor: 'var(--dataops-success-bg)', padding: '2px 8px', borderRadius: '4px'
                          }}>
                            <ShieldCheck size={12} /> Se protege al procesar
                          </span>
                        </td>
                        <td>
                          <span className="chip-cat chip-fecha">[{item.status}]</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <Button
                              variant="ghost"
                              type="button"
                              onClick={() => handleTogglePreview(item)}
                              style={{ padding: '4px 8px', fontSize: '11px' }}
                            >
                              {isExpanded ? 'Ocultar' : 'Vista previa'}
                            </Button>
                            <Button
                              variant="ghost"
                              type="button"
                              onClick={() => handleRemoveFile(item.uid)}
                              disabled={isProcessing || isCheckingFiles}
                              aria-label={`Quitar ${item.file.name}`}
                              title="Quitar archivo"
                              style={{ padding: '4px 8px' }}
                            >
                              <Trash2 size={13} />
                            </Button>
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={{ padding: 0 }}>
                            <div className="dataops-row-detail">
                              <span><strong>Archivo:</strong> {item.file.name}</span>
                              <span><strong>Tamaño:</strong> {fileSize}</span>
                              <span><strong>Origen:</strong> {tipoLabel}</span>
                              <span><strong>Fechas:</strong> Por detectar al procesar</span>
                              <span><strong>Estado:</strong> {item.status}</span>
                            </div>
                            <div style={{ padding: '12px 16px', borderTop: '1px solid var(--color-border)', backgroundColor: 'var(--color-alabaster)' }}>
                              {loadingPreviewUid === item.uid ? (
                                <p role="status" style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>Analizando hojas y encabezados del libro…</p>
                              ) : workbookPreviews[item.uid] ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', fontSize: 12 }}>
                                    <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-ink-black)' }}>
                                      Hojas totales: <strong>{workbookPreviews[item.uid].resumen_hojas?.total ?? 0}</strong>
                                    </span>
                                    <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)' }}>
                                      Usadas: <strong>{workbookPreviews[item.uid].resumen_hojas?.usadas ?? 0}</strong>
                                    </span>
                                    <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)' }}>
                                      Ignoradas: <strong>{workbookPreviews[item.uid].resumen_hojas?.ignoradas ?? 0}</strong>
                                    </span>
                                    <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                                      Ocultas: <strong>{workbookPreviews[item.uid].resumen_hojas?.ocultas ?? 0}</strong>
                                    </span>
                                  </div>
                                  <div tabIndex={0} role="region" aria-label={`Hojas de ${item.file.name}`} style={{ overflowX: 'auto' }}>
                                    <table className="dataops-table" style={{ width: '100%', fontSize: 12 }}>
                                      <thead>
                                        <tr>
                                          <th scope="col">Hoja</th>
                                          <th scope="col">Visibilidad</th>
                                          <th scope="col">Decisión</th>
                                          <th scope="col">Motivo</th>
                                          <th scope="col">Filas estimadas</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {(workbookPreviews[item.uid].hojas || []).map((h) => (
                                          <tr key={h.hoja}>
                                            <td><strong>{h.hoja}</strong></td>
                                            <td>{h.estado_visibilidad}</td>
                                            <td>
                                              <span style={{
                                                padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
                                                backgroundColor: h.decision === 'usada' ? 'var(--dataops-success-bg)' : 'var(--dataops-warning-bg)',
                                                color: h.decision === 'usada' ? 'var(--dataops-success-text)' : 'var(--dataops-warning-text)',
                                              }}>
                                                {h.decision}
                                              </span>
                                            </td>
                                            <td style={{ color: 'var(--color-slate-gray)' }}>{h.motivo}</td>
                                            <td style={{ fontVariantNumeric: 'tabular-nums' }}>{(h.filas_estimadas ?? 0).toLocaleString('es-BO')}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                  {workbookPreviews[item.uid].mapeo_columnas?.length > 0 && (
                                    <div tabIndex={0} role="region" aria-label={`Mapeo de columnas de ${item.file.name}`} style={{ overflowX: 'auto' }}>
                                      <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: 6 }}>Mapeo editable columna → campo canónico</p>
                                      <table className="dataops-table" style={{ width: '100%', fontSize: 12 }}>
                                        <thead>
                                          <tr>
                                            <th scope="col">Columna del archivo</th>
                                            <th scope="col">Hoja</th>
                                            <th scope="col">Campo canónico</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {workbookPreviews[item.uid].mapeo_columnas.map((m) => (
                                            <tr key={`${m.hoja}-${m.columna_origen}`}>
                                              <td>{m.columna_origen}</td>
                                              <td style={{ color: 'var(--color-slate-gray)' }}>{m.hoja}</td>
                                              <td>
                                                <select
                                                  className="dataops-select"
                                                  aria-label={`Campo canónico para ${m.columna_origen}`}
                                                  value={m.campo_canonico || ''}
                                                  onChange={(e) => handleChangeColumnMapping(item.uid, m.columna_origen, e.target.value)}
                                                  style={{ padding: '4px 8px', fontSize: 11.5 }}
                                                >
                                                  <option value="">Sin asignar…</option>
                                                  {(workbookPreviews[item.uid].campos_canonicos_disponibles || []).map((c) => (
                                                    <option key={c} value={c}>{c}</option>
                                                  ))}
                                                </select>
                                              </td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>Sin datos de vista previa disponibles.</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            <Paginacion {...queuePagination} onChange={queuePagination.setPagina} />
          </div>
        ) : inspectedFiles.length > 0 ? (
          <>
          {prepKpis && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 14 }}>
              {prepKpis.map(([label, value]) => (
                <div key={label} style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid var(--color-border)', backgroundColor: 'var(--color-mist-gray)' }}>
                  <p style={{ color: 'var(--color-slate-gray)', fontSize: 11.5, margin: 0 }}>{label}</p>
                  <p style={{ color: 'var(--color-ink-black)', fontSize: 20, fontWeight: 700, margin: '4px 0 0' }}>
                    {value == null ? 'Sin dato' : <AnimatedNumberV2 value={value.toLocaleString('es-BO')} />}
                  </p>
                </div>
              ))}
            </div>
          )}
          <div style={{ overflowX: 'auto', maxWidth: '100%', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table className="dataops-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Origen detectado</th>
                  <th>Filas</th>
                  <th>Protección</th>
                  <th>Estado</th>
                  <th style={{ textAlign: 'center' }}>Vista previa</th>
                </tr>
              </thead>
              <tbody>
                {inspectedPagination.visibles.map((item) => {
                  const isExpanded = expandedDetailKey === item.key;
                  return (
                    <React.Fragment key={item.key}>
                      <tr className="dataops-table-row" style={{ cursor: 'default' }}>
                        <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileSpreadsheet size={15} color="var(--color-gira-gold)" />
                            <span>{item.nombre}</span>
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 400, marginTop: '3px' }}>
                            {item.origen} · Registros: {item.filas} · Fechas: {item.fechas}
                          </div>
                        </td>
                        <td>
                          <span className="chip-cat chip-origen" style={{ fontWeight: 700 }}>
                            {item.origen}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{item.filas}</td>
                        <td>
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: '4px',
                            fontSize: '11px', fontWeight: 700, color: 'var(--color-alert-green)',
                            backgroundColor: 'var(--dataops-success-bg)', padding: '2px 8px', borderRadius: '4px'
                          }}>
                            <ShieldCheck size={12} /> Protección del servidor
                          </span>
                        </td>
                        <td>
                          <span className="chip-cat chip-fecha">[{item.estado}]</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <Button
                            variant="ghost"
                            type="button"
                            onClick={() => setExpandedDetailKey(isExpanded ? null : item.key)}
                            style={{ padding: '4px 10px', fontSize: '11px' }}
                          >
                            {isExpanded ? 'Ocultar' : 'Vista previa'}
                          </Button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={6} style={{ padding: 0 }}>
                            <div className="dataops-row-detail">
                              <span><strong>Archivo:</strong> {item.nombre}</span>
                              <span><strong>Origen:</strong> {item.origen}</span>
                              <span><strong>Registros:</strong> {item.filas}</span>
                              <span><strong>Fechas:</strong> {item.fechas}</span>
                              <span><strong>Estado:</strong> {item.estado}</span>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            <Paginacion {...inspectedPagination} onChange={inspectedPagination.setPagina} />
          </div>
          </>
        ) : (
          <div style={{ padding: '36px', textAlign: 'center', backgroundColor: 'var(--color-mist-gray)', borderRadius: '10px', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            No hay archivos en la cola. Arrastra archivos en la zona de carga o selecciona un lote del historial para inspeccionar.
          </div>
        )}
      </div>

      <BatchHistory
        inspecting={isLoadingBatchData}
        disabled={isProcessing || isCheckingFiles}
        onInspect={(src) => {
          setActiveBatchId(src.id_lote);
          setExpandedDetailKey(null);
          localStorage.setItem('last_active_batch_id', String(src.id_lote));
          loadBatchInspection(src.id_lote);
        }}
        onLogs={handleOpenTelemetry}
        onNewBatch={handleNewBatch}
        loadingLogs={loadingLogs}
      />

      {/* ─── DRAWER DE BITÁCORA TÉCNICA Y REPORTE MARKDOWN (.MD) ─── */}
      <PipelineTelemetryDrawer
        key={telemetryDoc?.id_documento || 'sin-documento'}
        isOpen={telemetryOpen}
        onClose={() => setTelemetryOpen(false)}
        docId={telemetryDoc?.id_documento}
        docMeta={telemetryDoc}
      />
    </BatchFlowLayout>
  );
}
