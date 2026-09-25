import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, CheckCircle, AlertCircle, X,
  FileSpreadsheet, FileText, Trash2, Plus, Sparkles, ArrowRight
} from 'lucide-react';
import { dataopsApi } from '../../../api/dataopsApi';
import { sileoToast } from '../../../services/sileoToast';
import { useNotifications } from '../../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../../constants/systemConstants';
import {
  detectSourceType,
  formatFileSize,
  SOURCE_TYPES,
  getSourceTypeMeta
} from '../../../utils/fileTypeDetector';

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const navigate = useNavigate();
  // filesList holds: [ { file: File, id: string, sourceType: string, isAutoDetected: boolean } ]
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedToProcess, setSelectedToProcess] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageText, setStageText] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [uploadResult, setUploadResult] = useState(null);

  const fileInputRef = useRef(null);
  const { notify } = useNotifications();

  if (!isOpen) return null;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const addFiles = (incomingFiles) => {
    const validFiles = Array.from(incomingFiles).filter((f) => {
      const ext = f.name.toLowerCase();
      return (
        ext.endsWith('.xlsx') ||
        ext.endsWith('.xls') ||
        ext.endsWith('.csv') ||
        ext.endsWith('.xml')
      );
    });

    if (validFiles.length === 0) {
      setError('Formato no soportado. Por favor seleccione archivos .xlsx, .xls, .csv o .xml.');
      return;
    }

    setError('');
    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((item) => item.file.name));
      const newItems = validFiles
        .filter((file) => !existingNames.has(file.name))
        .map((file) => ({
          file,
          id: `${file.name}-${Date.now()}-${Math.random()}`,
          sourceType: detectSourceType(file),
          isAutoDetected: true,
        }));
      return [...prev, ...newItems];
    });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
    }
    // Reset input so same file can be selected again if removed
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRemoveFile = (idToRemove) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== idToRemove));
  };

  const handleChangeSourceType = (id, newType) => {
    setSelectedFiles((prev) =>
      prev.map((item) =>
        item.id === id
          ? { ...item, sourceType: newType, isAutoDetected: false }
          : item
      )
    );
  };

  const resetState = () => {
    setSelectedFiles([]);
    setSelectedToProcess([]);
    setIsUploading(false);
    setProgress(0);
    setStageText('');
    setError('');
    setUploadResult(null);
  };

  const handleToggleSelectToProcess = (fileName) => {
    setSelectedToProcess((prev) =>
      prev.includes(fileName)
        ? prev.filter((name) => name !== fileName)
        : [...prev, fileName]
    );
  };

  const handleSelectAllToProcess = () => {
    if (selectedToProcess.length === selectedFiles.length) {
      setSelectedToProcess([]);
    } else {
      setSelectedToProcess(selectedFiles.map((item) => item.file.name));
    }
  };

  const handleClose = () => {
    if (uploadResult && onUploadSuccess) {
      onUploadSuccess(uploadResult);
    }
    resetState();
    onClose();
  };

  const handleStayInSources = () => {
    if (onUploadSuccess) {
      onUploadSuccess(uploadResult);
    }
    resetState();
    onClose();
  };

  const handleGoToPhase2 = () => {
    if (selectedToProcess.length === 0) {
      sileoToast.warning({
        title: 'Selección Requerida',
        description: 'Debe marcar al menos un archivo para procesar en Fase 2.'
      });
      return;
    }
    const result = uploadResult;
    if (onUploadSuccess) {
      onUploadSuccess(result);
    }
    const filesParam = encodeURIComponent(selectedToProcess.join(','));
    resetState();
    onClose();
    navigate(`/dataops/procesamiento?autoRun=true&files=${filesParam}`);
  };

  const startUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Por favor seleccione al menos un archivo para continuar.');
      return;
    }

    setIsUploading(true);
    setProgress(15);
    setStageText(`Preparando lote de ${selectedFiles.length} archivo(s)...`);
    setError('');

    const t1 = setTimeout(() => {
      setProgress(45);
      setStageText('Inspeccionando firmas y enrutando con Dispatcher...');
    }, 700);

    const t2 = setTimeout(() => {
      setProgress(80);
      setStageText('Normalizando cabeceras canónicas e insertando a Staging...');
    }, 1400);

    try {
      const filesWithTypes = selectedFiles.map((item) => ({
        file: item.file,
        sourceType: item.sourceType,
      }));

      const uploadBatchPromise = dataopsApi.uploadBatch(filesWithTypes, (pct) => {
        if (pct > 20 && pct < 90) setProgress(pct);
      });

      sileoToast.promise(uploadBatchPromise, {
        loading: { title: 'Ingestando Fuentes Documentales...', description: 'Calculando firmas SHA-256 y clasificando archivos' },
        success: (res) => ({ title: 'Lote Ingerido con Éxito', description: `${res?.total_archivos || selectedFiles.length} archivo(s) catalogados y validados.` }),
        error: (err) => ({ title: 'Falla de Ingesta', description: 'Error al procesar el lote documental en el servidor.' })
      });

      const res = await uploadBatchPromise;

      clearTimeout(t1);
      clearTimeout(t2);

      setProgress(100);
      setStageText('Lote procesado y catalogado exitosamente.');

      notify({
        title: 'Ingesta Multi-Archivo Completada',
        message: `${selectedFiles.length} fuente(s) procesada(s) y validadas en el pipeline institucional.`,
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/fuentes',
      });

      setIsUploading(false);
      setUploadResult(res || { status: 'success' });
      const filesToProcess = selectedFiles.map((item) => item.file.name);
      setSelectedToProcess(filesToProcess);

      sileoToast.action({
        title: 'Fuentes Listas para Pipeline',
        description: `${filesToProcess.length} archivo(s) seleccionados. ¿Desea iniciar la normalización ahora?`,
        button: {
          title: 'Ir a Fase 2',
          onClick: () => {
            onClose();
            navigate(`/dataops/procesamiento?autoRun=true&files=${encodeURIComponent(filesToProcess.join(','))}`);
          }
        }
      });
    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      setIsUploading(false);
      setError(
        'Error durante el procesamiento del lote. Verifique la estructura de los archivos e intente nuevamente.'
      );
    }
  };

  const getFileIcon = (fileName) => {
    const lower = fileName.toLowerCase();
    if (lower.endsWith('.csv')) {
      return <FileText size={20} color="#4338ca" />;
    }
    return <FileSpreadsheet size={20} color="var(--color-alert-green)" />;
  };

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(23, 25, 28, 0.55)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1300,
        padding: '20px',
      }}
    >
      <div
        className="modal-panel floating-artifact"
        style={{
          padding: '28px 32px',
          borderRadius: 'var(--radius-cards)',
          width: '100%',
          maxWidth: '620px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-modal)',
          position: 'relative',
          backgroundColor: 'var(--color-paper-white)',
          color: 'var(--color-ink-black)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '18px',
            flexShrink: 0,
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: 'var(--color-sienna-brown)',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Sparkles size={13} /> DataOps · Ingesta Multi-Archivo (1..N)
            </span>
            <h3
              className="serif-heading"
              style={{
                fontSize: '22px',
                margin: '4px 0 0 0',
                color: 'var(--color-ink-black)',
              }}
            >
              Carga Inteligente de Fuentes Documentales
            </h3>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading}
            type="button"
            style={{
              background: 'none',
              border: 'none',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              color: 'var(--color-slate-gray)',
              padding: '6px',
              borderRadius: '6px',
            }}
            title="Cerrar ventana"
          >
            <X size={20} />
          </button>
        </div>

        {uploadResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div style={{ textAlign: 'center', padding: '16px 0 20px' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(34, 197, 94, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                }}
              >
                <CheckCircle size={32} color="var(--color-alert-green)" />
              </div>
              <h4
                className="serif-heading"
                style={{ fontSize: '20px', margin: '0 0 6px', color: 'var(--color-ink-black)' }}
              >
                ¡Archivos Ingeridos y Catalogados con Éxito!
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: 0 }}>
                {uploadResult.message || `${selectedFiles.length} fuente(s) procesada(s) y listas para homologación en el pipeline.`}
              </p>
            </div>

            {/* Resumen de archivos procesados con selección interactiva para Fase 2 */}
            <div
              style={{
                backgroundColor: 'var(--color-fog-white)',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '14px 16px',
                marginBottom: '16px',
                maxHeight: '220px',
                overflowY: 'auto',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '12px',
                  paddingBottom: '8px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--color-slate-gray)',
                    letterSpacing: '0.6px',
                  }}
                >
                  Seleccionar Fuentes para Fase 2 ({selectedToProcess.length} de {selectedFiles.length})
                </div>
                <button
                  type="button"
                  onClick={handleSelectAllToProcess}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '11.5px',
                    color: 'var(--color-sienna-brown)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: '2px 6px',
                    borderRadius: '4px',
                  }}
                >
                  {selectedToProcess.length === selectedFiles.length
                    ? 'Deseleccionar todos'
                    : 'Seleccionar todos'}
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedFiles.map((item) => {
                  const isChecked = selectedToProcess.includes(item.file.name);
                  return (
                    <label
                      key={item.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '13px',
                        color: 'var(--color-ink-black)',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        backgroundColor: isChecked ? 'var(--color-paper-white)' : 'transparent',
                        border: isChecked ? '1px solid var(--color-gira-gold)' : '1px solid var(--color-border)',
                        boxShadow: isChecked ? 'var(--shadow-subtle)' : 'none',
                        cursor: 'pointer',
                        userSelect: 'none',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          minWidth: 0,
                          flex: 1,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleSelectToProcess(item.file.name)}
                          style={{
                            accentColor: 'var(--color-sienna-brown)',
                            width: '16px',
                            height: '16px',
                            cursor: 'pointer',
                            flexShrink: 0,
                          }}
                        />
                        <div style={{ flexShrink: 0 }}>
                          {getFileIcon(item.file.name)}
                        </div>
                        <span
                          style={{
                            fontWeight: isChecked ? 600 : 400,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            maxWidth: '300px',
                            color: isChecked ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
                          }}
                        >
                          {item.file.name}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          backgroundColor: isChecked
                            ? 'rgba(34, 197, 94, 0.12)'
                            : 'rgba(100, 116, 139, 0.1)',
                          color: isChecked
                            ? 'var(--color-alert-green)'
                            : 'var(--color-slate-gray)',
                          fontWeight: 600,
                          flexShrink: 0,
                        }}
                      >
                        {isChecked ? 'Listo' : 'Omitido'}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Aviso si no hay ninguno seleccionado */}
            {selectedToProcess.length === 0 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'var(--color-alert-amber)',
                  backgroundColor: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  marginBottom: '14px',
                }}
              >
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>Debe seleccionar al menos un archivo para procesar en Fase 2.</span>
              </div>
            )}

            {/* Acciones de la pantalla de éxito */}
            <div
              style={{
                display: 'flex',
                gap: '12px',
                justifyContent: 'flex-end',
                alignItems: 'center',
                marginTop: 'auto',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border)',
              }}
            >
              <button
                type="button"
                className="btn-pill-ghost"
                onClick={handleStayInSources}
                style={{ padding: '9px 20px', fontSize: '13px' }}
              >
                Permanecer en Fuentes
              </button>
              <button
                type="button"
                className="btn-pill-dark"
                onClick={handleGoToPhase2}
                style={{
                  padding: '10px 24px',
                  fontSize: '13.5px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-ink-black)',
                  color: 'var(--color-paper-white)',
                  opacity: selectedToProcess.length === 0 ? 0.45 : 1,
                  cursor: selectedToProcess.length === 0 ? 'not-allowed' : 'pointer',
                  transition: 'opacity 0.2s ease',
                }}
                title={
                  selectedToProcess.length === 0
                    ? 'Seleccione al menos un archivo para continuar'
                    : 'Enviar seleccionados a Fase 2'
                }
              >
                Procesar en Fase 2 ({selectedToProcess.length} seleccionados) →
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Hidden Multi-file input */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".xlsx,.csv,.xls,.xml"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

        {/* Drag and Drop Zone */}
        <div
          className="drop-zone"
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          style={{
            border: dragActive
              ? '2px dashed var(--color-ink-black)'
              : '2px dashed var(--color-border)',
            backgroundColor: dragActive
              ? 'var(--color-mist-gray)'
              : 'var(--color-fog-white)',
            borderRadius: '16px',
            padding: '24px 20px',
            textAlign: 'center',
            marginBottom: '18px',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
            flexShrink: 0,
          }}
        >
          <UploadCloud
            size={36}
            color="var(--color-slate-gray)"
            style={{ margin: '0 auto 8px' }}
          />
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-ink-black)',
              margin: 0,
              fontWeight: 600,
            }}
          >
            Arrastra de 1 a N archivos aquí o haz clic para explorar
          </p>
          <p
            style={{
              fontSize: '12px',
              color: 'var(--color-ash-gray)',
              marginTop: '4px',
              marginBottom: 0,
            }}
          >
            Auto-clasificación inteligente: .xlsx (Actas), .csv (Forms), Moodle (.xml/.csv), Cartera (.xlsx)
          </p>
        </div>

        {/* Selected Files Interactive List */}
        {selectedFiles.length > 0 && (
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              marginBottom: '18px',
              paddingRight: '4px',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
              }}
            >
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--color-slate-gray)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.6px',
                }}
              >
                Archivos Seleccionados ({selectedFiles.length})
              </span>
              <button
                type="button"
                onClick={() => !isUploading && fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '12px',
                  color: 'var(--color-sienna-brown)',
                  fontWeight: 600,
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <Plus size={14} /> Agregar más archivos
              </button>
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                maxHeight: '220px',
              }}
            >
              {selectedFiles.map((item) => {
                const meta = getSourceTypeMeta(item.sourceType);
                return (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      backgroundColor: 'var(--color-fog-white)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '10px',
                      gap: '12px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        minWidth: 0,
                        flex: 1,
                      }}
                    >
                      <div style={{ flexShrink: 0 }}>
                        {getFileIcon(item.file.name)}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          style={{
                            fontSize: '13.5px',
                            fontWeight: 600,
                            color: 'var(--color-ink-black)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                          title={item.file.name}
                        >
                          {item.file.name}
                        </div>
                        <div
                          style={{
                            fontSize: '11px',
                            color: 'var(--color-slate-gray)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {formatFileSize(item.file.size)}
                        </div>
                      </div>
                    </div>

                    {/* Source Type Selector Badge */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        flexShrink: 0,
                      }}
                    >
                      <div style={{ position: 'relative' }}>
                        <select
                          value={item.sourceType}
                          onChange={(e) =>
                            handleChangeSourceType(item.id, e.target.value)
                          }
                          disabled={isUploading}
                          style={{
                            fontSize: '11.5px',
                            fontWeight: 600,
                            padding: '4px 10px',
                            borderRadius: '9999px',
                            border: `1px solid ${meta.color}40`,
                            backgroundColor: meta.bg,
                            color: meta.color,
                            cursor: isUploading ? 'not-allowed' : 'pointer',
                            outline: 'none',
                          }}
                          title="Haga clic para reclasificar el tipo documental si es necesario"
                        >
                          {SOURCE_TYPES.map((st) => (
                            <option key={st} value={st}>
                              {st}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Remove Button */}
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(item.id)}
                        disabled={isUploading}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: isUploading ? 'not-allowed' : 'pointer',
                          color: 'var(--color-ash-gray)',
                          padding: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          borderRadius: '4px',
                          transition: 'color 0.15s ease',
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.color =
                            'var(--color-alert-red)')
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.color =
                            'var(--color-ash-gray)')
                        }
                        title="Descartar este archivo"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Progress Bar & Stage Indicator */}
        {isUploading && (
          <div style={{ marginBottom: '18px', flexShrink: 0 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '12.5px',
                marginBottom: '6px',
              }}
            >
              <span
                style={{
                  color: 'var(--color-ink-black)',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {progress === 100 ? (
                  <CheckCircle size={15} color="var(--color-alert-green)" />
                ) : null}
                {stageText}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: 'var(--color-ink-black)',
                }}
              >
                {progress}%
              </span>
            </div>
            <div
              style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'var(--color-mist-gray)',
                borderRadius: '9999px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${progress}%`,
                  height: '100%',
                  backgroundColor:
                    progress === 100
                      ? 'var(--color-alert-green)'
                      : 'var(--color-sienna-brown)',
                  borderRadius: '9999px',
                  transition: 'width 0.4s ease, background-color 0.3s ease',
                }}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--color-alert-red)',
              backgroundColor: 'rgba(217, 56, 58, 0.1)',
              border: '1px solid rgba(217, 56, 58, 0.25)',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '12.5px',
              marginBottom: '16px',
              flexShrink: 0,
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Action buttons */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end',
            alignItems: 'center',
            marginTop: 'auto',
            paddingTop: '12px',
            borderTop: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            className="btn-pill-ghost"
            onClick={handleClose}
            disabled={isUploading}
            style={{ padding: '9px 20px', fontSize: '13px' }}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn-pill-dark"
            onClick={startUpload}
            disabled={isUploading || selectedFiles.length === 0}
            style={{
              padding: '10px 24px',
              fontSize: '13.5px',
              opacity: isUploading || selectedFiles.length === 0 ? 0.6 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              fontWeight: 600,
            }}
          >
            {isUploading ? (
              'Procesando Lote...'
            ) : (
              <>
                <UploadCloud size={16} />
                Iniciar Carga ({selectedFiles.length}{' '}
                {selectedFiles.length === 1 ? 'archivo' : 'archivos'})
              </>
            )}
          </button>
        </div>
          </>
        )}
      </div>
    </div>
  );
}
