import React, { useState, useEffect, useRef } from 'react';
import { Eye, RotateCcw } from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import BatchHistory from './components/BatchHistory';
import IngestDropzonePanel from './components/IngestDropzonePanel';
import IngestRulesPanel from './components/IngestRulesPanel';
import IngestQueueTable from './components/IngestQueueTable';
import IngestWorkbookPreview from './components/IngestWorkbookPreview';
import IngestBatchFilesTable from './components/IngestBatchFilesTable';
import Button from '../../components/shared/Button';
import usePaginacion from '../../hooks/usePaginacion';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { clearLoteFlowSession } from './context/LoteFlowContext';
import useTextoPreparado from './hooks/useTextoPreparado';
import useResumenPreparacion from './hooks/useResumenPreparacion';
import { dataopsApi } from '../../api/dataopsApi';
import { mensajeError } from '../../utils/mensajeError';
import { confirmar, sileoToast } from '../../services/sileoToast';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { inspectFileHeaders, validateFileSecurityClient, isAcademicSourceType, toCanonicalSourceCode } from '../../utils/fileTypeDetector';
import { MAX_ARCHIVOS_POR_LOTE, getTipoFuenteLabel } from '../../constants/dataopsConfig';
import { getSelectedQueueFiles, isAllQueueSelected, validateQueueSelection } from './utils/cargaHistorialHelpers';

export default function IngestView() {
  const [queuedFiles, setQueuedFiles] = useState([]);
  const [selectedQueueUids, setSelectedQueueUids] = useState([]);
  const [expandedDetailKey, setExpandedDetailKey] = useState(null);
  const institucion = 'GiraGroup Posgrado';
  const processingRef = useRef(false);
  const uploadAbortRef = useRef(null);
  const dropzoneRef = useRef(null);
  const queueCheckRef = useRef(false);
  const [isCheckingFiles, setIsCheckingFiles] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isResettingBatch, setIsResettingBatch] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStageText, setUploadStageText] = useState('');
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [activeBatchData, setActiveBatchData] = useState(null);
  const [isLoadingBatchData, setIsLoadingBatchData] = useState(false);
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [telemetryDoc, setTelemetryDoc] = useState(null);
  const [workbookPreviews, setWorkbookPreviews] = useState({});
  const [loadingPreviewUid, setLoadingPreviewUid] = useState(null);

  const loadBatchInspection = async (batchId) => {
    if (!batchId) return;
    try {
      setIsLoadingBatchData(true);
      setActiveBatchData(null);
      const batchRes = await dataopsApi.getLoteContext(batchId);
      if (batchRes && batchRes.archivos) setActiveBatchData(batchRes);
    } catch {
      sileoToast.error({ title: 'No se pudo cargar la vista previa', description: 'Selecciona de nuevo el lote para reintentarlo.' });
    } finally { setIsLoadingBatchData(false); }
  };

  useEffect(() => {
    (async () => {
      try {
        const lastId = localStorage.getItem('last_active_batch_id');
        let reanudable = !!lastId;
        if (reanudable) {
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
      } catch {
        sileoToast.error({ title: 'No se pudo recuperar el lote', description: 'Selecciona un lote del historial para continuar.' });
      }
    })();
  }, []);

  const handleTogglePreview = async (item) => {
    if (expandedDetailKey === item.uid) { setExpandedDetailKey(null); return; }
    setExpandedDetailKey(item.uid);
    if (workbookPreviews[item.uid] || loadingPreviewUid === item.uid) return;
    setLoadingPreviewUid(item.uid);
    try {
      const prev = await dataopsApi.previewWorkbook(item.file, item.sourceType || null);
      setWorkbookPreviews((curr) => ({ ...curr, [item.uid]: prev }));
    } catch (err) {
      sileoToast.error({ title: 'No se pudo generar la vista previa', description: mensajeError(err) });
    } finally { setLoadingPreviewUid(null); }
  };

  const handleChangeColumnMapping = (uid, columnaOrigen, nuevoCampo) => {
    setWorkbookPreviews((curr) => {
      const prev = curr[uid];
      if (!prev) return curr;
      return { ...curr, [uid]: { ...prev, mapeo_columnas: (prev.mapeo_columnas || []).map((m) => m.columna_origen === columnaOrigen ? { ...m, campo_canonico: nuevoCampo } : m) } };
    });
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
    } catch { sileoToast.error({ title: 'No se pudo abrir la bitácora', description: 'Inténtalo de nuevo.' }); }
    finally { setLoadingLogs(null); }
  };

  const handleNewBatch = () => {
    if (activeBatchId) clearLoteFlowSession(activeBatchId);
    localStorage.removeItem('last_active_batch_id');
    setActiveBatchId(null); setActiveBatchData(null); setQueuedFiles([]); setSelectedQueueUids([]); setExpandedDetailKey(null);
    queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    dropzoneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    dropzoneRef.current?.focus({ preventScroll: true });
  };

  const handleClearQueue = async () => {
    if (processingRef.current || queueCheckRef.current || queuedFiles.length === 0) return;
    const ok = await confirmar({
      title: 'Vaciar cola de archivos',
      description: `Se quitarán ${queuedFiles.length} archivo(s) pendientes de la cola.`,
      confirmText: 'Vaciar cola',
    });
    if (!ok) return;
    setQueuedFiles([]); setSelectedQueueUids([]); setExpandedDetailKey(null);
  };

  const handleCancelUpload = async () => {
    if (!processingRef.current) return;
    const ok = await confirmar({
      title: 'Cancelar carga en curso',
      description: 'Se detendrá la carga del lote actual para que puedas corregir los archivos.',
      confirmText: 'Cancelar carga',
    });
    if (!ok) return;
    uploadAbortRef.current?.abort();
    try {
      const activas = await dataopsApi.getTareasActivas();
      const ingestaActiva = (activas || []).find((t) => t.tipo === 'INGESTA' && t.estado === 'EN_CURSO');
      if (ingestaActiva?.id) {
        await dataopsApi.cancelarTarea(ingestaActiva.id);
      }
    } catch { /* Si ya terminó o no hay tarea registrada, basta abortar la petición HTTP. */ }
    processingRef.current = false;
    setIsProcessing(false);
    setUploadProgress(0);
    setUploadStageText('');
  };

  const handleResetBatch = async () => {
    if (!activeBatchId || processingRef.current || queueCheckRef.current || isResettingBatch) return;
    const ok = await confirmar({
      title: `Reiniciar lote #${activeBatchId}`,
      description: 'Se eliminará este lote y sus archivos cargados en staging para que puedas volver a subir los archivos correctos.',
      confirmText: 'Reiniciar lote',
    });
    if (!ok) return;
    setIsResettingBatch(true);
    try {
      const idBorrado = activeBatchId;
      await dataopsApi.reiniciarLote(idBorrado);
      clearLoteFlowSession(idBorrado);
      localStorage.removeItem('last_active_batch_id');
      setActiveBatchId(null);
      setActiveBatchData(null);
      setQueuedFiles([]);
      setSelectedQueueUids([]);
      setExpandedDetailKey(null);
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      sileoToast.success({ title: `Lote #${idBorrado} reiniciado`, description: 'Puedes cargar los archivos correctos ahora.' });
    } catch (err) {
      sileoToast.error({ title: 'No se pudo reiniciar el lote', description: mensajeError(err) });
    } finally {
      setIsResettingBatch(false);
    }
  };

  const addFilesToQueue = async (fileList) => {
    const incoming = Array.from(fileList || []);
    if (!incoming.length || processingRef.current || queueCheckRef.current) return;
    if (queuedFiles.length + incoming.length > MAX_ARCHIVOS_POR_LOTE) {
      sileoToast.error({ title: 'Límite de archivos por lote excedido', description: `Se permiten máximo ${MAX_ARCHIVOS_POR_LOTE} archivos simultáneos por lote.` });
      return;
    }
    queueCheckRef.current = true; setIsCheckingFiles(true);
    try {
      const validItems = [];
      for (const f of incoming) {
        const sec = validateFileSecurityClient(f);
        if (!sec.valid) { sileoToast.error({ title: 'Archivo rechazado por validación', description: sec.error }); continue; }
        const headerResult = await inspectFileHeaders(f);
        const canonicalCode = headerResult.recognized ? toCanonicalSourceCode(headerResult.code) : '';
        validItems.push({ uid: `${f.name}_${f.size}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, file: f, sourceType: canonicalCode, tipoEscala: isAcademicSourceType(canonicalCode) ? '' : null, status: 'En cola' });
      }
      if (validItems.length > 0) {
        setQueuedFiles((prev) => [...prev, ...validItems]);
        setSelectedQueueUids((prev) => [...prev, ...validItems.map((it) => it.uid)]);
        const unrecognizedCount = validItems.filter((it) => !it.sourceType).length;
        if (unrecognizedCount > 0) sileoToast.warning({ title: `${unrecognizedCount} archivo(s) sin tipo reconocido`, description: 'Seleccione manualmente el tipo documental en los selectores correspondientes.' });
        else sileoToast.success({ title: `${validItems.length} archivo(s) añadido(s) al lote`, description: 'Cabeceras y tipo documental verificados automáticamente.' });
      }
    } catch { sileoToast.error({ title: 'No se pudieron revisar los archivos', description: 'Selecciona los archivos de nuevo.' }); }
    finally { queueCheckRef.current = false; setIsCheckingFiles(false); }
  };

  const handleRemoveFile = (uid) => {
    if (processingRef.current || queueCheckRef.current) return;
    setQueuedFiles((prev) => prev.filter((item) => item.uid !== uid));
    setSelectedQueueUids((prev) => prev.filter((id) => id !== uid));
    if (expandedDetailKey === uid) setExpandedDetailKey(null);
  };

  const handleChangeFileSourceType = (uid, newCode) => {
    setQueuedFiles((prev) => prev.map((item) => item.uid !== uid ? item : { ...item, sourceType: newCode, tipoEscala: isAcademicSourceType(newCode) ? (item.tipoEscala || '') : null, status: 'En cola' }));
  };

  const selectedQueueFiles = getSelectedQueueFiles(queuedFiles, selectedQueueUids);
  const allQueueSelected = isAllQueueSelected(queuedFiles, selectedQueueUids);
  const isFormValid = validateQueueSelection(selectedQueueFiles, MAX_ARCHIVOS_POR_LOTE, institucion).valid;

  const handleProcessBatch = async () => {
    if (!isFormValid || processingRef.current || isCheckingFiles) return;
    processingRef.current = true;
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    const filesToSend = selectedQueueFiles;
    try {
      setIsProcessing(true); setUploadProgress(0);
      setUploadStageText(`Transfiriendo ${filesToSend.length} archivo(s) al servidor...`);
      sileoToast.info({ title: 'Cargando archivos', description: `Se enviarán ${filesToSend.length} archivo(s) para procesar.` });
      const payload = filesToSend.map((it) => ({ file: it.file, sourceType: it.sourceType, tipoEscala: isAcademicSourceType(it.sourceType) ? it.tipoEscala : null }));
      const uploadRes = await dataopsApi.uploadBatch(payload, (pct) => {
        setUploadProgress(pct);
        if (pct < 100) setUploadStageText(`Subiendo archivos al servidor: ${pct}% completado...`);
        else {
          setUploadStageText('Archivos transferidos. El servidor está procesando el lote (normalización, fechas y pre-etiquetado)...');
          avisarTareaIniciada();
          sileoToast.info({ title: 'Archivos transferidos al servidor', description: 'La ingesta sigue en el servidor. Puedes cambiar de página: te avisaremos al terminar.' });
        }
      }, { institucion, periodo: 'Auto' }, controller.signal);
      const perFileResults = uploadRes?.archivos_procesados || uploadRes?.resultados || [];
      const loteId = uploadRes?.id_lote || uploadRes?.doc_ids?.[0];
      const exitosos = uploadRes?.archivos_exitosos ?? 0;
      const fallidos = perFileResults.filter(r => r.status !== 'procesado');
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      const resultByUid = new Map();
      filesToSend.forEach((it, idx) => { if (perFileResults[idx]) resultByUid.set(it.uid, perFileResults[idx]); });
      const processedUids = new Set();
      setQueuedFiles(prev => prev.map((it) => {
        const r = resultByUid.get(it.uid);
        if (!r) return it;
        if (r.status === 'procesado') { processedUids.add(it.uid); return null; }
        return { ...it, sourceType: toCanonicalSourceCode(r.tipo_fuente) || it.sourceType, status: 'Por revisar' };
      }).filter(Boolean));
      setSelectedQueueUids((prev) => prev.filter((uid) => !processedUids.has(uid)));
      if (fallidos.length) sileoToast.warning({ title: `${fallidos.length} archivo(s) sin procesar`, description: fallidos.map(r => `${r.nombre_archivo}: ${r.mensaje || 'Revisa el archivo.'}`).join('\n') });
      if (loteId && exitosos > 0) {
        localStorage.setItem('last_active_batch_id', String(loteId));
        setActiveBatchId(Number(loteId));
        await loadBatchInspection(Number(loteId));
        sileoToast.success({ title: `Lote #${loteId} procesado exitosamente`, description: `${exitosos} archivo(s) cargados. Ya puedes revisar su contenido.` });
      }
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED' || controller.signal.aborted) {
        sileoToast.info({ title: 'Carga cancelada', description: 'Se detuvo la transferencia. Puedes corregir los archivos y volver a intentarlo.' });
      } else {
        sileoToast.error({ title: 'Error en ingesta de lote', description: mensajeError(err, 'No se pudieron procesar los archivos. Inténtalo de nuevo.') });
      }
    } finally { uploadAbortRef.current = null; processingRef.current = false; setIsProcessing(false); setUploadStageText(''); }
  };

  const inspectedFiles = (activeBatchData?.archivos || []).map((a, index) => ({
    key: `lote_${activeBatchId || 'x'}_${a.id_documento || index}`,
    nombre: a.nombre_archivo || 'Sin dato', size: 'Sin dato',
    origen: getTipoFuenteLabel(a.tipo_fuente) || a.tipo_fuente || 'Sin dato',
    filas: a.total_registros ?? 'Sin dato', fechas: activeBatchData?.rango_fechas || 'Sin dato', estado: 'Texto listo',
  }));
  const queuePagination = usePaginacion(queuedFiles);
  const inspectedPagination = usePaginacion(inspectedFiles);
  const { data: prepResumen } = useTextoPreparado(activeBatchId, null, 1, !!activeBatchId && inspectedFiles.length > 0);
  const prepKpis = useResumenPreparacion(prepResumen);
  const previewItem = queuedFiles.find((it) => it.uid === expandedDetailKey);

  return (
    <BatchFlowLayout currentStep={1}>
      <div className="dataops-section-a" style={{ marginBottom: '28px' }}>
        <IngestDropzonePanel
          dropzoneRef={dropzoneRef} isDragging={isDragging} setIsDragging={setIsDragging}
          isProcessing={isProcessing} isCheckingFiles={isCheckingFiles} uploadProgress={uploadProgress}
          isFormValid={isFormValid} queuedFiles={queuedFiles} selectedQueueFiles={selectedQueueFiles}
          onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.length) addFilesToQueue(e.dataTransfer.files); }}
          onFileSelect={(e) => { if (e.target.files?.length) { addFilesToQueue(e.target.files); e.target.value = ''; } }}
          onProcessBatch={handleProcessBatch} onClearQueue={handleClearQueue} onCancelUpload={handleCancelUpload}
        />
        <IngestRulesPanel isProcessing={isProcessing} uploadProgress={uploadProgress} uploadStageText={uploadStageText} onCancelUpload={handleCancelUpload} />
      </div>

      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }} aria-busy={isLoadingBatchData}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="var(--color-gira-gold)" /> {queuedFiles.length > 0 ? 'Cola de archivos' : 'Archivos del lote'}
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              {queuedFiles.length > 0 ? 'Selecciona los archivos a procesar, verifica su tipo documental y revisa su detalle en cada fila.' : 'Detalle de los archivos del lote inspeccionado.'}
            </p>
          </div>
          {queuedFiles.length > 0 ? (
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}><strong>{selectedQueueFiles.length}</strong> de <strong>{queuedFiles.length}</strong> seleccionado(s)</span>
          ) : inspectedFiles.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>Mostrando <strong>{inspectedFiles.length}</strong> archivo(s) del lote #{activeBatchId}</span>
              {activeBatchData?.estado_flujo !== 'CONSOLIDADO' && (
                <Button
                  variant="ghost"
                  className="dataops-btn-danger"
                  disabled={isProcessing || isCheckingFiles || isLoadingBatchData || isResettingBatch}
                  isLoading={isResettingBatch}
                  loadingText="Reiniciando…"
                  onClick={handleResetBatch}
                >
                  <RotateCcw size={13} /> Reiniciar lote
                </Button>
              )}
              <Button variant="ghost" disabled={isProcessing || isCheckingFiles || isLoadingBatchData || isResettingBatch} onClick={handleNewBatch}>Limpiar vista</Button>
            </div>
          ) : null}
        </div>

        {isLoadingBatchData ? (
          <p role="status" style={{ color: 'var(--color-slate-gray)', fontSize: '13px' }}>Cargando información del lote…</p>
        ) : queuedFiles.length > 0 ? (
          <>
            <IngestQueueTable
              queuedFiles={queuedFiles} queuePagination={queuePagination} selectedQueueUids={selectedQueueUids}
              setSelectedQueueUids={setSelectedQueueUids} allQueueSelected={allQueueSelected} expandedDetailKey={expandedDetailKey}
              isProcessing={isProcessing} isCheckingFiles={isCheckingFiles} onChangeFileSourceType={handleChangeFileSourceType}
              onChangeFileScale={(uid, val) => setQueuedFiles(prev => prev.map(f => f.uid === uid ? { ...f, tipoEscala: val } : f))}
              onTogglePreview={handleTogglePreview} onRemoveFile={handleRemoveFile}
            />
            <IngestWorkbookPreview
              previewItem={previewItem} previewData={previewItem ? workbookPreviews[previewItem.uid] : null}
              loading={previewItem && loadingPreviewUid === previewItem.uid}
              onClose={() => setExpandedDetailKey(null)} onChangeColumnMapping={handleChangeColumnMapping}
            />
          </>
        ) : inspectedFiles.length > 0 ? (
          <IngestBatchFilesTable prepKpis={prepKpis} inspectedPagination={inspectedPagination} expandedDetailKey={expandedDetailKey} onToggleExpand={setExpandedDetailKey} />
        ) : (
          <div style={{ padding: '36px', textAlign: 'center', backgroundColor: 'var(--color-mist-gray)', borderRadius: '10px', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            No hay archivos en la cola. Arrastra archivos en la zona de carga o selecciona un lote del historial para inspeccionar.
          </div>
        )}
      </div>

      <BatchHistory
        inspecting={isLoadingBatchData} disabled={isProcessing || isCheckingFiles}
        onInspect={(src) => { setActiveBatchId(src.id_lote); setExpandedDetailKey(null); localStorage.setItem('last_active_batch_id', String(src.id_lote)); loadBatchInspection(src.id_lote); }}
        onLogs={handleOpenTelemetry} onNewBatch={handleNewBatch} loadingLogs={loadingLogs}
      />
      <PipelineTelemetryDrawer key={telemetryDoc?.id_documento || 'sin-documento'} isOpen={telemetryOpen} onClose={() => setTelemetryOpen(false)} docId={telemetryDoc?.id_documento} docMeta={telemetryDoc} />
    </BatchFlowLayout>
  );
}
