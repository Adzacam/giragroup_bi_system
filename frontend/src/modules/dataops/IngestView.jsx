import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle, Play,
  HelpCircle, Eye, Layers, RefreshCw, Trash2, Check, Scale, Sparkles, XCircle, Terminal
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import PipelineTelemetryDrawer from './components/PipelineTelemetryDrawer';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
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

  // Cola multi-archivo (#15, #16, #17, #18)
  // Cada item: { uid, file, sourceType: 'ACTA'|'MOODLE'|'COBRANZA'|'ADMISION'|'', recognized: bool, matchedKeywords: [], tipoEscala: ''|'CENTESIMAL_100'|'DECIMAL_10'|'VIGESIMAL_20', status: null|'procesado'|'duplicado'|'error_validacion', statusDetail: '' }
  const [queuedFiles, setQueuedFiles] = useState([]);
  const [institucion, setInstitucion] = useState('Unifranz');
  const [periodo, setPeriodo] = useState('2026-1');
  const [escalaGlobalAcademica, setEscalaGlobalAcademica] = useState('CENTESIMAL_100');

  // Estados de proceso y UI
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [sourcesHistory, setSourcesHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  // Estados del Drawer de Bitácora Técnica y Reporte Markdown (.MD)
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [telemetryDoc, setTelemetryDoc] = useState(null);
  const [telemetryLogs, setTelemetryLogs] = useState([]);
  const [telemetryMarkdown, setTelemetryMarkdown] = useState('');
  const [telemetryMetrics, setTelemetryMetrics] = useState(null);

  // Vista previa dinámica generada desde el primer archivo CSV/seleccionado
  const [previewFileIndex, setPreviewFileIndex] = useState(0);
  const [previewRows, setPreviewRows] = useState([]);
  const [previewColumns, setPreviewColumns] = useState([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await dataopsApi.getSources();
      if (res && res.data) {
        setSourcesHistory(res.data);
      }
    } catch (err) {
      console.warn('Error al cargar historial:', err);
    } finally {
      setIsLoadingHistory(false);
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

  const generateCsvPreview = (f) => {
    if (!f) {
      setPreviewColumns([]);
      setPreviewRows([]);
      return;
    }
    const ext = f.name.split('.').pop().toLowerCase();
    if (ext === 'csv') {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const text = e.target.result;
          const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
          if (lines.length > 0) {
            const separator = lines[0].includes(';') ? ';' : lines[0].includes('|') ? '|' : ',';
            const rawHeaders = lines[0].split(separator).map((h) => h.trim().replace(/^["']|["']$/g, ''));
            const cols = rawHeaders.map((h, i) => ({
              key: `col_${i}`,
              label: h,
              recognized: [
                'nombre', 'estudiante', 'ci', 'cedula', 'modulo', 'materia',
                'nota', 'calificacion', 'asistencia', 'monto', 'deuda', 'cuota', 'concepto', 'idnumber', 'course'
              ].some((k) => h.toLowerCase().includes(k)),
            }));
            const rows = lines.slice(1, 6).map((line, rIdx) => {
              const vals = line.split(separator).map((v) => v.trim().replace(/^["']|["']$/g, ''));
              const rowObj = { id: rIdx + 1 };
              rawHeaders.forEach((_, cIdx) => {
                rowObj[`col_${cIdx}`] = vals[cIdx] || '';
              });
              return rowObj;
            });
            setPreviewColumns(cols);
            setPreviewRows(rows);
          }
        } catch (err) {
          console.warn('Error parseando CSV en cliente:', err);
        }
      };
      reader.readAsText(f.slice(0, 10000));
    } else {
      setPreviewColumns([]);
      setPreviewRows([]);
    }
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

      // Inspección prioritaria de las primeras 5 filas / cabeceras reales (#15)
      const headerResult = await inspectFileHeaders(f);
      const canonicalCode = headerResult.recognized ? toCanonicalSourceCode(headerResult.code) : '';

      if (f.name.toLowerCase().includes('unifranz') && !institucion) {
        setInstitucion('Unifranz');
      }

      validItems.push({
        uid: `${f.name}_${f.size}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        file: f,
        sourceType: canonicalCode, // '' cuando no se reconoce (#15: Nunca asumir Acta por defecto)
        recognized: headerResult.recognized,
        matchedKeywords: headerResult.matchedKeywords || [],
        tipoEscala: isAcademicSourceType(canonicalCode) ? (escalaGlobalAcademica || 'CENTESIMAL_100') : null,
        status: null,
        statusDetail: '',
      });
    }

    if (validItems.length > 0) {
      setQueuedFiles((prev) => {
        const next = [...prev, ...validItems];
        if (prev.length === 0 && next.length > 0) {
          setPreviewFileIndex(0);
          generateCsvPreview(next[0].file);
        }
        return next;
      });

      const unrecognizedCount = validItems.filter((it) => !it.sourceType).length;
      if (unrecognizedCount > 0) {
        sileoToast.warning({
          title: `${unrecognizedCount} archivo(s) sin tipo reconocido`,
          description: 'Seleccione manualmente el tipo documental en los selectores con borde ámbar.',
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
    setQueuedFiles((prev) => {
      const next = prev.filter((item) => item.uid !== uid);
      if (next.length === 0) {
        setPreviewColumns([]);
        setPreviewRows([]);
        setPreviewFileIndex(0);
      } else if (previewFileIndex >= next.length) {
        setPreviewFileIndex(0);
        generateCsvPreview(next[0].file);
      }
      return next;
    });
  };

  const handleChangeFileSourceType = (uid, newCode) => {
    setQueuedFiles((prev) =>
      prev.map((item) => {
        if (item.uid !== uid) return item;
        const academic = isAcademicSourceType(newCode);
        return {
          ...item,
          sourceType: newCode,
          // Si pasa a COBRANZA o ADMISION, escala es null (#16)
          tipoEscala: academic ? (item.tipoEscala || escalaGlobalAcademica || 'CENTESIMAL_100') : null,
          status: null,
          statusDetail: '',
        };
      })
    );
  };

  const handleChangeFileEscala = (uid, newEscala) => {
    setQueuedFiles((prev) =>
      prev.map((item) => (item.uid === uid ? { ...item, tipoEscala: newEscala } : item))
    );
  };

  const handleApplyScaleToAllAcademic = () => {
    if (!escalaGlobalAcademica) {
      sileoToast.warning({
        title: 'Seleccione una escala primero',
        description: 'Elija una escala en el selector rápido para aplicarla a los archivos académicos.',
      });
      return;
    }
    let updatedCount = 0;
    setQueuedFiles((prev) =>
      prev.map((item) => {
        if (isAcademicSourceType(item.sourceType)) {
          updatedCount += 1;
          return { ...item, tipoEscala: escalaGlobalAcademica };
        }
        return { ...item, tipoEscala: null };
      })
    );
    sileoToast.success({
      title: 'Escala aplicada',
      description: `Se asignó ${escalaGlobalAcademica} a ${updatedCount} archivo(s) académico(s).`,
    });
  };

  // Validaciones estrictas del lote (#15, #16, #18)
  const hasAcademicFiles = queuedFiles.some((it) => isAcademicSourceType(it.sourceType));
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
      sileoToast.info({
        title: 'Iniciando ingestión de lote',
        description: `Procesando ${queuedFiles.length} archivo(s) con validación SHA-256 y cabeceras...`,
      });

      const payload = queuedFiles.map((it) => ({
        file: it.file,
        sourceType: it.sourceType,
        tipoEscala: isAcademicSourceType(it.sourceType) ? it.tipoEscala : null,
      }));

      const uploadRes = await dataopsApi.uploadBatch(
        payload,
        (pct) => setUploadProgress(pct),
        { institucion, periodo }
      );
      const perFileResults = uploadRes?.archivos_procesados || uploadRes?.resultados || [];

      if (perFileResults.length > 0) {
        setQueuedFiles((prev) =>
          prev.map((it, idx) => {
            const match = perFileResults[idx] || perFileResults.find((r) => r.nombre_archivo === it.file.name);
            if (!match) return it;
            return {
              ...it,
              status: match.estado || match.status || 'procesado',
              statusDetail: match.detalle || match.mensaje || '',
            };
          })
        );
      }

      const loteId = uploadRes?.id_lote || uploadRes?.doc_ids?.[0] || perFileResults[0]?.id_documento;
      const processedCount =
        uploadRes?.files_processed ??
        uploadRes?.archivos_exitosos ??
        perFileResults.filter((r) => (r.estado || r.status) === 'procesado').length;

      if (loteId && processedCount > 0) {
        localStorage.setItem('last_active_batch_id', String(loteId));
        await loadHistory();

        sileoToast.success({
          title: `Lote #${loteId} procesado (${processedCount} archivo${processedCount === 1 ? '' : 's'})`,
          description: 'Avanzando al Paso ②: Texto plano estructurado',
        });

        navigate(`/dataops/lote/${loteId}/texto`);
      } else {
        sileoToast.warning({
          title: 'Ningún archivo nuevo fue procesado',
          description: 'Revise el estado individual por archivo (duplicado SHA-256 o error de validación).',
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
    }
  };

  return (
    <BatchFlowLayout currentStep={1}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '24px', marginBottom: '28px' }}>
        
        {/* ─── Columna Izquierda: Subir y Configurar Archivos del Lote ─── */}
        <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
                Subir archivos al lote ({queuedFiles.length}/{MAX_ARCHIVOS_POR_LOTE})
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: 0 }}>
                Formatos admitidos: <strong>.xlsx, .xls, .csv</strong> (máx. {MAX_TAMANO_ARCHIVO_MB} MB por archivo). Se inspeccionan las cabeceras reales.
              </p>
            </div>
            {queuedFiles.length > 0 && (
              <button
                onClick={() => {
                  setQueuedFiles([]);
                  setPreviewColumns([]);
                  setPreviewRows([]);
                }}
                className="sileo-btn"
                style={{
                  padding: '6px 10px', fontSize: '11px', borderRadius: '8px',
                  backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                  color: 'var(--color-slate-gray)', cursor: 'pointer'
                }}
              >
                Vaciar cola
              </button>
            )}
          </div>

          {/* Zona Drag & Drop */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            style={{
              border: isDragging ? '2px dashed #2563eb' : '2px dashed var(--color-border)',
              backgroundColor: isDragging ? 'rgba(37, 99, 235, 0.04)' : 'var(--color-mist-gray)',
              borderRadius: '14px',
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
              accept=".xlsx,.xls,.csv"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              backgroundColor: '#eff6ff', color: '#2563eb',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <UploadCloud size={22} />
            </div>

            <div style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
              Arrastra de 1 a {MAX_ARCHIVOS_POR_LOTE} archivos aquí o haz click para explorar
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--color-ash-gray)' }}>
              Detección automática por cabeceras de columna · Rechazo estricto de .xml y archivos &gt; {MAX_TAMANO_ARCHIVO_MB} MB
            </div>
          </div>

          {/* Lista de archivos en cola con tipo y escala por archivo (#15, #16, #18) */}
          {queuedFiles.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '360px', overflowY: 'auto' }}>
              {queuedFiles.map((item, idx) => {
                const isAcademic = isAcademicSourceType(item.sourceType);
                const needsSource = !item.sourceType;
                const needsScale = isAcademic && !item.tipoEscala;

                return (
                  <div
                    key={item.uid}
                    onClick={() => {
                      setPreviewFileIndex(idx);
                      generateCsvPreview(item.file);
                    }}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: needsSource || needsScale
                        ? '1.5px solid #f59e0b'
                        : item.status === 'duplicado' || item.status === 'error_validacion'
                        ? '1.5px solid #ef4444'
                        : '1px solid var(--color-border)',
                      backgroundColor: previewFileIndex === idx ? 'var(--dataops-row-selected)' : 'var(--color-paper-white)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                        <FileSpreadsheet size={16} color="#2563eb" style={{ flexShrink: 0 }} />
                        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-ink-black)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.file.name}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--color-ash-gray)', flexShrink: 0 }}>
                          ({formatFileSize(item.file.size)})
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {item.recognized ? (
                          <span style={{
                            fontSize: '10.5px', padding: '2px 7px', borderRadius: '999px',
                            backgroundColor: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0', fontWeight: '600'
                          }}>
                            ✓ Cabecera reconocida
                          </span>
                        ) : (
                          <span style={{
                            fontSize: '10.5px', padding: '2px 7px', borderRadius: '999px',
                            backgroundColor: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', fontWeight: '700'
                          }}>
                            ⚠ Sin reconocer
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(item.uid);
                          }}
                          style={{ background: 'none', border: 'none', color: 'var(--color-ash-gray)', cursor: 'pointer', padding: '2px' }}
                          title="Quitar archivo"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Selectores por archivo: Tipo Documental y Escala condicional (#15, #16) */}
                    <div style={{ display: 'grid', gridTemplateColumns: isAcademic ? '1fr 1fr' : '1fr', gap: '10px' }} onClick={(e) => e.stopPropagation()}>
                      <div>
                        <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: needsSource ? '#b45309' : 'var(--color-slate-gray)', marginBottom: '4px' }}>
                          Tipo documental *
                        </label>
                        <select
                          value={item.sourceType}
                          onChange={(e) => handleChangeFileSourceType(item.uid, e.target.value)}
                          className="dataops-select"
                          style={{
                            padding: '6px 10px',
                            fontSize: '12px',
                            border: needsSource ? '1.5px solid #f59e0b' : undefined,
                            backgroundColor: needsSource ? '#fffbeb' : undefined,
                          }}
                        >
                          <option value="">{UNRECOGNIZED_SOURCE_LABEL}</option>
                          {TIPOS_FUENTE_DATAOPS.map((tf) => (
                            <option key={tf.code} value={tf.code}>
                              {tf.label} ({tf.code})
                            </option>
                          ))}
                        </select>
                      </div>

                      {isAcademic ? (
                        <div>
                          <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: needsScale ? '#b45309' : 'var(--color-slate-gray)', marginBottom: '4px' }}>
                            Escala de notas *
                          </label>
                          <select
                            value={item.tipoEscala || ''}
                            onChange={(e) => handleChangeFileEscala(item.uid, e.target.value)}
                            className="dataops-select"
                            style={{
                              padding: '6px 10px',
                              fontSize: '12px',
                              border: needsScale ? '1.5px solid #f59e0b' : undefined,
                              backgroundColor: needsScale ? '#fffbeb' : undefined,
                            }}
                          >
                            <option value="">-- Elegir escala --</option>
                            {ESCALAS_ACADEMICAS.map((esc) => (
                              <option key={esc.value} value={esc.value}>
                                {esc.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : item.sourceType ? (
                        <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', alignSelf: 'end', paddingBottom: '4px' }}>
                          Escala de notas: <strong>No aplica ({item.sourceType})</strong>
                        </div>
                      ) : null}
                    </div>

                    {/* Estado individual tras subida (#18) */}
                    {item.status && (
                      <div style={{
                        fontSize: '11.5px',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        backgroundColor: item.status === 'procesado' ? '#ecfdf5' : '#fef2f2',
                        color: item.status === 'procesado' ? '#059669' : '#dc2626',
                      }}>
                        {item.status === 'procesado' ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        <strong>{item.status.toUpperCase()}:</strong> {item.statusDetail}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ─── Columna Derecha: Datos del Lote y Regla de Escala ─── */}
        <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column' }}>
          <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 8px 0', color: 'var(--color-ink-black)' }}>
            Datos del lote
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 20px 0' }}>
            Configura los metadatos institucionales y aplica la escala de calificación a los archivos académicos.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
            {/* Institución */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Institución *
              </label>
              <select
                value={institucion}
                onChange={(e) => setInstitucion(e.target.value)}
                className="dataops-select"
              >
                <option value="">-- Seleccionar Institución --</option>
                <option value="Unifranz">Universidad Franz Tamayo (Unifranz)</option>
                <option value="Univalle">Universidad Privada del Valle (Univalle)</option>
                <option value="UPB">Universidad Privada Boliviana (UPB)</option>
                <option value="UCB">Universidad Católica Boliviana (UCB)</option>
              </select>
            </div>

            {/* Periodo */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                Periodo académico
              </label>
              <select
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className="dataops-select"
              >
                <option value="2026-1">Gestión 2026 - Periodo 1</option>
                <option value="2025-2">Gestión 2025 - Periodo 2</option>
                <option value="2025-1">Gestión 2025 - Periodo 1</option>
              </select>
            </div>

            {/* Aplicación rápida de escala a todos los archivos académicos (#16) */}
            <div style={{
              padding: '14px',
              borderRadius: '12px',
              backgroundColor: 'var(--color-mist-gray)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '700', color: 'var(--color-ink-black)' }}>
                <Scale size={15} color="#2563eb" /> Escala para archivos académicos (ACTA / MOODLE)
              </label>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <select
                  value={escalaGlobalAcademica}
                  onChange={(e) => {
                    const val = e.target.value;
                    setEscalaGlobalAcademica(val);
                    if (val) {
                      setQueuedFiles((prev) =>
                        prev.map((item) =>
                          isAcademicSourceType(item.sourceType)
                            ? { ...item, tipoEscala: val }
                            : item
                        )
                      );
                    }
                  }}
                  className="dataops-select"
                  style={{ flex: 1, minWidth: '200px' }}
                >
                  <option value="">-- Seleccionar escala académica --</option>
                  {ESCALAS_ACADEMICAS.map((esc) => (
                    <option key={esc.value} value={esc.value}>
                      {esc.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleApplyScaleToAllAcademic}
                  disabled={!escalaGlobalAcademica || !hasAcademicFiles}
                  className="sileo-btn"
                  style={{
                    padding: '8px 14px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '700',
                    backgroundColor: escalaGlobalAcademica && hasAcademicFiles ? '#2563eb' : 'var(--color-paper-white)',
                    color: escalaGlobalAcademica && hasAcademicFiles ? '#ffffff' : 'var(--color-ash-gray)',
                    border: '1px solid var(--color-border)',
                    cursor: escalaGlobalAcademica && hasAcademicFiles ? 'pointer' : 'not-allowed',
                  }}
                >
                  Aplicar escala a todos los archivos académicos
                </button>
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>
                Normalización automática a base 100: <strong>0–10 → ×10</strong> · <strong>0–20 → ×5</strong> · <strong>0–100 → ×1</strong>. Los archivos de Cobranza y Admisión no llevan escala.
              </div>
            </div>

            {/* Avisos de validación pendientes */}
            {(missingSourceTypeCount > 0 || missingScaleCount > 0) && (
              <div className="dataops-banner-warning" style={{ fontSize: '12.5px' }}>
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                <div>
                  {missingSourceTypeCount > 0 && (
                    <div>• Hay <strong>{missingSourceTypeCount}</strong> archivo(s) sin tipo documental reconocido. Seleccione su tipo manualmente.</div>
                  )}
                  {missingScaleCount > 0 && (
                    <div>• Hay <strong>{missingScaleCount}</strong> archivo(s) académico(s) sin escala de calificación asignada.</div>
                  )}
                </div>
              </div>
            )}

            {/* Texto de ayuda explicativo */}
            <div className="dataops-banner-info" style={{ marginTop: 'auto' }}>
              <HelpCircle size={18} color="var(--dataops-info-text)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Regla de negocio:</strong> El sistema inspecciona las cabeceras reales de cada archivo, calcula su hash SHA-256 completo para evitar duplicados y nunca asume "Acta" ni la escala de notas por defecto.
              </div>
            </div>

            {/* Botón de Procesar */}
            <button
              onClick={handleProcessBatch}
              disabled={!isFormValid || isProcessing}
              className="sileo-btn"
              style={{
                marginTop: '8px',
                padding: '14px 20px',
                borderRadius: '12px',
                backgroundColor: isFormValid ? '#2563eb' : 'var(--color-mist-gray)',
                color: isFormValid ? '#ffffff' : 'var(--color-ash-gray)',
                border: 'none',
                fontWeight: '700',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: isFormValid ? 'pointer' : 'not-allowed',
                transition: 'all 0.2s ease',
                boxShadow: isFormValid ? '0 4px 12px rgba(37, 99, 235, 0.25)' : 'none'
              }}
            >
              {isProcessing ? (
                <>
                  <RefreshCw size={18} className="animate-spin" /> Procesando Lote ({uploadProgress}%)...
                </>
              ) : (
                <>
                  <Play size={18} fill="currentColor" /> Procesar lote ({queuedFiles.length} {queuedFiles.length === 1 ? 'archivo' : 'archivos'})
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Vista Previa con Columnas Detectadas ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={18} color="#2563eb" /> Vista previa de estructura de archivo
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Verificación previa de columnas reconocidas ✓ y validación antes del procesamiento
            </p>
          </div>
          {previewRows.length > 0 && (
            <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#10b981', fontWeight: '600' }}>
                <Check size={14} /> {previewColumns.filter((c) => c.recognized).length} Reconocidas
              </span>
              <span style={{ color: 'var(--color-border)' }}>·</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#f59e0b', fontWeight: '600' }}>
                <AlertTriangle size={14} /> {previewColumns.filter((c) => !c.recognized).length} Adicionales
              </span>
            </div>
          )}
        </div>

        {previewRows.length > 0 ? (
          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', width: '50px', color: 'var(--color-slate-gray)' }}>#</th>
                  {previewColumns.map((col, idx) => (
                    <th key={idx} style={{ padding: '10px 14px', color: 'var(--color-ink-black)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{col.label}</span>
                        {col.recognized ? (
                          <span style={{ color: '#10b981', fontSize: '11px', display: 'inline-flex', alignItems: 'center' }} title="Reconocida por el dispatcher">
                            ✓
                          </span>
                        ) : (
                          <span style={{ color: '#f59e0b', fontSize: '11px', display: 'inline-flex', alignItems: 'center' }} title="Columna adicional">
                            ⚠
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row) => (
                  <tr key={row.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>{row.id}</td>
                    {previewColumns.map((col, cIdx) => (
                      <td key={cIdx} style={{ padding: '10px 14px', color: 'var(--color-ink-black)' }}>
                        {row[col.key] || '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : queuedFiles.length > 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', backgroundColor: 'var(--color-mist-gray)', borderRadius: '10px', border: '1px dashed var(--color-border)' }}>
            <FileSpreadsheet size={32} color="#2563eb" style={{ margin: '0 auto 8px auto', display: 'block' }} />
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-ink-black)' }}>
              {queuedFiles[previewFileIndex]?.file?.name} ({formatFileSize(queuedFiles[previewFileIndex]?.file?.size)})
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>
              Archivo en cola listo para ingestión. El backend analizará todas las hojas y filas en el Paso ② Texto plano estructurado.
            </div>
          </div>
        ) : (
          <div style={{ padding: '36px 16px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '10px' }}>
            Arrastra o selecciona archivos arriba para inspeccionar sus cabeceras antes del procesamiento.
          </div>
        )}
      </div>

      {/* ─── Historial de Lotes y Archivos ─── */}
      <div className="floating-artifact" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
              Historial de lotes y fuentes procesadas
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Accede directamente a los pasos ② Texto plano, ③ Lectura BETO, ④ Revisión o abre la Bitácora Técnica y Reporte Markdown (.MD)
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => handleOpenTelemetry(sourcesHistory[0] || { id: 1, nombre_archivo: 'Lote Reciente' })}
              className="sileo-btn"
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                backgroundColor: '#0f172a',
                color: '#38bdf8',
                border: '1px solid #334155',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 600
              }}
            >
              <Terminal size={13} /> 📋 Bitácora Técnica (.MD)
            </button>
            <button
              onClick={loadHistory}
              className="sileo-btn"
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                backgroundColor: 'var(--color-mist-gray)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <RefreshCw size={13} /> Actualizar
            </button>
          </div>
        </div>

        {isLoadingHistory ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            Cargando historial de lotes...
          </div>
        ) : sourcesHistory.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13px' }}>
            No hay lotes previos. Carga un archivo arriba para comenzar.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Lote / Archivo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Tipo</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Escala</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Registros</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>Fecha</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-slate-gray)' }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {sourcesHistory.map((src) => {
                  const navId = src.id_lote || src.id || src.id_documento;
                  const fileName = src.nombre_archivo || src.name || `Documento_${navId}`;
                  const sourceType = src.tipo_fuente || src.tipo_documento || src.type || 'ACTA';
                  const recordCount = src.registros_detectados ?? src.total_registros ?? src.records ?? 0;
                  const dateDisplay = src.fecha_carga
                    ? new Date(src.fecha_carga).toLocaleDateString()
                    : (src.date || 'Reciente');
                  return (
                    <tr key={src.id || src.id_documento} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                        {src.id_lote ? <span style={{ color: '#2563eb', fontFamily: 'var(--font-mono)', marginRight: '6px' }}>[Lote #{src.id_lote}]</span> : null}
                        {fileName}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-slate-gray)' }}>
                        {sourceType}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontSize: '12px' }}>
                        {src.tipo_escala || 'No aplica'}
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                        {recordCount}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)', fontSize: '12px' }}>
                        {dateDisplay}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            onClick={() => handleOpenTelemetry(src)}
                            className="sileo-btn"
                            title="Ver bitácora técnica y reporte Markdown (.MD)"
                            style={{
                              padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                              backgroundColor: '#0f172a', color: '#38bdf8', border: '1px solid #334155',
                              fontWeight: '600', cursor: 'pointer'
                            }}
                          >
                            📋 Bitácora Técnica
                          </button>
                          <button
                            onClick={() => navigate(`/dataops/lote/${navId}/texto`)}
                            className="sileo-btn"
                            style={{
                              padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                              backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)',
                              cursor: 'pointer'
                            }}
                          >
                            ② Texto
                          </button>
                          <button
                            onClick={() => navigate(`/dataops/lote/${navId}/beto`)}
                            className="sileo-btn"
                            style={{
                              padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                              backgroundColor: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', border: '1px solid var(--dataops-info-border)',
                              fontWeight: '600', cursor: 'pointer'
                            }}
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

      {/* Drawer de Bitácora Técnica y Reporte Markdown (.MD) */}
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

