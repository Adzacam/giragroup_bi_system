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
} from '../../constants/dataopsConfig';

export default function IngestView() {

  // ─── Estado de la cola multi-archivo (zona de carga) ───
  const [queuedFiles, setQueuedFiles] = useState([]);
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

  // ─── Estado de Lote Activo para lista de archivos y Sección C (Split View) ───
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [activeBatchData, setActiveBatchData] = useState(null);
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
    setTelemetryLogs([]);
    setTelemetryMarkdown('');
    setTelemetryMetrics(null);
    try {
      const res = await dataopsApi.getLogs(docId);
      setTelemetryDoc({ ...src, id: docId });
      setTelemetryLogs(res.data || []);
      setTelemetryMarkdown(res.markdown_report || '');
      setTelemetryMetrics(res.summary_metrics || null);
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
    setSelectedInspectionIndex(0);
    queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    dropzoneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    dropzoneRef.current?.focus({ preventScroll: true });
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
    if (!isFormValid || processingRef.current || isCheckingFiles) return;
    processingRef.current = true;

    try {
      setIsProcessing(true);
      setUploadProgress(0);
      setUploadStageText(`Transfiriendo ${queuedFiles.length} archivo(s) al servidor...`);
      sileoToast.info({
        title: 'Cargando archivos',
        description: `Se enviarán ${queuedFiles.length} archivo(s) para procesar.`,
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

      const exitosos = uploadRes?.archivos_exitosos ?? 0;
      const fallidos = perFileResults.filter(r => r.status !== 'procesado');
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      setQueuedFiles(prev => prev.filter((it, idx) => perFileResults[idx]?.status !== 'procesado').map(it => ({ ...it, status: 'Por revisar' })));
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

  // ─── Datos de la lista de archivos (Tabla de Lote del Dispatcher) ───
  const batchTableItems = queuedFiles.length > 0
    ? queuedFiles.map((q, index) => ({
        index, nombre: q.file.name, size: formatFileSize(q.file.size),
        origen: TIPOS_FUENTE_DATAOPS.find(t => t.code === q.sourceType)?.label || 'Por seleccionar',
        filas: q.resultRecords ?? 'Sin dato', fechas: 'Por detectar',
        estado: q.status, isQueued: true,
      }))
    : (activeBatchData?.archivos || []).map((a, index) => ({
        index, nombre: a.nombre_archivo || 'Sin dato', size: 'Sin dato',
        origen: TIPOS_FUENTE_DATAOPS.find(t => t.code === a.tipo_fuente)?.label || 'Sin dato',
        filas: a.total_registros ?? 'Sin dato', fechas: activeBatchData.rango_fechas || 'Sin dato',
        estado: 'Texto listo', isQueued: false,
      }));
  const filesPagination = usePaginacion(batchTableItems);
  const queuePagination = usePaginacion(queuedFiles);

  const currentSelectedFile = batchTableItems[selectedInspectionIndex] || batchTableItems[0] || null;

  return (
    <BatchFlowLayout currentStep={1}>
      {/* ─── SECCIÓN A: ZONA DE CARGA MULTIFUENTE Y CONFIGURACIÓN DE LOTE ─── */}
      <div className="dataops-section-a" style={{ marginBottom: '28px' }}>
        
        {/* Panel Izquierdo: Dropzone Multifichero (1 a N archivos) */}
        <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
                Cargar archivos
              </h2>
              <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
                Puedes cargar archivos de <strong>Exportaciones Moodle, Google Sheets</strong> (Actas Notas/Asistencia), <strong>Google Forms</strong> (Admisiones/Pagos). Hasta {MAX_ARCHIVOS_POR_LOTE} archivos .xlsx o .csv, de {MAX_TAMANO_ARCHIVO_MB} MB cada uno.
              </p>
            </div>
            {queuedFiles.length > 0 && (
              <Button variant="ghost"
                disabled={isProcessing || isCheckingFiles}
                onClick={() => setQueuedFiles([])}
                className="sileo-btn"
                style={{
                  padding: '5px 12px', fontSize: '11px', borderRadius: '6px',
                  backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                  color: 'var(--color-slate-gray)', cursor: 'pointer', fontWeight: 600
                }}
              >
                Vaciar cola ({queuedFiles.length})
              </Button>
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
              backgroundColor: 'var(--dataops-gold-bg)', color: 'var(--color-gira-gold, #D99B26)',
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

          {/* Lista de archivos en cola */}
          {queuedFiles.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
              {queuePagination.visibles.map((item) => {
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
                          {TIPOS_FUENTE_DATAOPS.find(t => t.code === item.sourceType)?.label || 'Por seleccionar'}
                        </span>
                        <Button variant="ghost"
                          type="button"
                          onClick={() => handleRemoveFile(item.uid)}
                          style={{ background: 'none', border: 'none', color: 'var(--color-ash-gray)', cursor: 'pointer', padding: '2px' }}
                          disabled={isProcessing || isCheckingFiles}
                          aria-label={`Quitar ${item.file.name}`}
                          title="Quitar archivo"
                        >
                          <Trash2 size={13} />
                        </Button>
                      </div>
                    </div>

                    {/* Selector de Tipo Documental si se requiere */}
                    <div style={{ display: 'grid', gridTemplateColumns: isAcademic ? '1fr 1fr' : '1fr', gap: '8px' }}>
                      <div>
                        <select
                          aria-label={`Tipo de archivo de ${item.file.name}`}
                          disabled={isProcessing}
                          value={item.sourceType}
                          onChange={(e) => handleChangeFileSourceType(item.uid, e.target.value)}
                          className="dataops-select"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                        >
                          <option value="">{UNRECOGNIZED_SOURCE_LABEL}</option>
                          {TIPOS_FUENTE_DATAOPS.map((tf) => (
                            <option key={tf.code} value={tf.code}>
                              {tf.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      {isAcademic && (
                        <div>
                          <select
                            value={item.tipoEscala || ''}
                            aria-label={`Escala de notas de ${item.file.name}`}
                            disabled={isProcessing}
                            onChange={(e) => {
                              const val = e.target.value;
                              setQueuedFiles(prev => prev.map(f => f.uid === item.uid ? { ...f, tipoEscala: val } : f));
                            }}
                            className="dataops-select"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                          >
                            <option value="">Selecciona la escala de notas</option>
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
              <Paginacion {...queuePagination} onChange={queuePagination.setPagina} />
            </div>
          )}
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
              marginBottom: '10px',
              padding: '12px 14px',
              borderRadius: '8px',
              backgroundColor: 'var(--dataops-gold-bg)',
              border: '1px solid var(--dataops-gold-border)',
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

          {/* Botón de Procesamiento Principal (Gold Pill) */}
          <Button variant="ghost"
            onClick={handleProcessBatch}
            isLoading={isProcessing}
            loadingText={uploadProgress < 100 ? `Subiendo archivos (${uploadProgress} %)…` : 'Procesando archivos…'}
            disabled={!isFormValid || isCheckingFiles}
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
                <Play size={16} fill="currentColor" /> Procesar archivos ({queuedFiles.length})
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ─── Archivos del lote (Tabla de Lote) ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="var(--color-gira-gold, #D99B26)" /> Archivos del lote
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Revisa el tipo de archivo y su estado antes de continuar.
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
            No hay archivos en la cola. Arrastra archivos en la zona de carga o selecciona un lote del historial para inspeccionar.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table className="dataops-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Archivo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Origen detectado</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Filas</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Protección</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Estado</th>
                  <th style={{ padding: '10px 14px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>Vista previa</th>
                </tr>
              </thead>
              <tbody>
                {filesPagination.visibles.map((item) => {
                  const idx = item.index;
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
                          fontSize: '11px', fontWeight: 700, color: 'var(--color-alert-green)',
                          backgroundColor: 'var(--dataops-success-bg)', padding: '2px 8px', borderRadius: '4px'
                        }}>
                          <ShieldCheck size={12} /> {item.isQueued ? 'Se protege al procesar' : 'Protección del servidor'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span className="chip-cat chip-fecha">
                          [{item.estado}]
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                        <Button variant="ghost"
                          type="button"
                          className="sileo-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedInspectionIndex(idx);
                          }}
                          style={{
                            padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                            backgroundColor: isSelected ? 'var(--color-gira-gold, #D99B26)' : 'var(--color-mist-gray)',
                            color: isSelected ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
                            border: '1px solid var(--color-border)',
                            cursor: 'pointer',
                            fontWeight: isSelected ? 700 : 500
                          }}
                        >
                          {isSelected ? 'Seleccionado' : 'Ver vista previa'}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <Paginacion {...filesPagination} onChange={filesPagination.setPagina} />
          </div>
        )}
      </div>

      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }} aria-busy={isLoadingBatchData}>
        <h3 className="serif-heading" style={{ fontSize: '18px', color: 'var(--color-ink-black)' }}>Archivo seleccionado</h3>
        {isLoadingBatchData ? <p role="status">Cargando información del lote…</p> : currentSelectedFile ? <>
          <p style={{ color: 'var(--color-ink-black)', margin: '12px 0' }}>{currentSelectedFile.nombre}</p>
          <p style={{ color: 'var(--color-slate-gray)' }}>{currentSelectedFile.origen} · Registros: {currentSelectedFile.filas} · {currentSelectedFile.estado}</p>
          <p style={{ color: 'var(--color-slate-gray)', fontSize: '12px', marginTop: '8px' }}>Continúa desde las acciones del historial para revisar el contenido del lote.</p>
        </> : <p style={{ color: 'var(--color-slate-gray)', margin: '12px 0' }}>Selecciona archivos para cargar o inspecciona un lote del historial.</p>}
        <Button variant="ghost" disabled={isProcessing || isCheckingFiles || isLoadingBatchData} onClick={handleNewBatch} style={{ marginTop: 12 }}>Limpiar selección</Button>
      </div>

      <BatchHistory
        inspecting={isLoadingBatchData}
        disabled={isProcessing || isCheckingFiles}
        onInspect={(src) => {
          setActiveBatchId(src.id_lote);
          setSelectedInspectionIndex(0);
          localStorage.setItem('last_active_batch_id', String(src.id_lote));
          loadBatchInspection(src.id_lote);
        }}
        onLogs={handleOpenTelemetry}
        onNewBatch={handleNewBatch}
        loadingLogs={loadingLogs}
      />

      {/* ─── DRAWER DE BITÁCORA TÉCNICA Y REPORTE MARKDOWN (.MD) ─── */}
      <PipelineTelemetryDrawer
        isOpen={telemetryOpen}
        onClose={() => setTelemetryOpen(false)}
        logs={telemetryLogs}
        onClearLogs={() => setTelemetryLogs([])}
        isProcessing={isProcessing}
        lotName={(telemetryDoc?.nombre_archivo || telemetryDoc?.name) ? `Archivo: ${telemetryDoc.nombre_archivo || telemetryDoc.name}` : 'Lote Activo'}
        sources={telemetryDoc ? [telemetryDoc] : []}
        activeDocId={telemetryDoc?.id_documento ?? null}
        markdownReport={telemetryMarkdown}
        summaryMetrics={telemetryMetrics}
      />
    </BatchFlowLayout>
  );
}
