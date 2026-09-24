import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, X, FileSpreadsheet } from 'lucide-react';
import { dataopsApi } from '../../../api/dataopsApi';
import { useNotifications } from '../../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../../constants/systemConstants';

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [sourceType, setSourceType] = useState('Acta de Calificaciones (Excel)');
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageText, setStageText] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');

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

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const startUpload = async () => {
    if (!file) {
      setError('Por favor seleccione un archivo para continuar.');
      return;
    }

    setIsUploading(true);
    setProgress(15);
    setStageText('Subiendo archivo al servidor...');
    setError('');

    // Simular progresión suave de etapas
    const t1 = setTimeout(() => {
      setProgress(55);
      setStageText('Validando y normalizando cabeceras canónicas...');
    }, 600);

    const t2 = setTimeout(() => {
      setProgress(85);
      setStageText('Detectando islas tabulares e insertando a Staging...');
    }, 1100);

    try {
      const res = await dataopsApi.uploadFile(file, sourceType);
      clearTimeout(t1);
      clearTimeout(t2);

      setProgress(100);
      setStageText('Registrado y catalogado exitosamente.');

      notify({
        title: 'Nueva Fuente Ingestada',
        message: `El archivo '${file.name}' (${sourceType}) fue validado y cargado al pipeline.`,
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/fuentes'
      });

      setTimeout(() => {
        setIsUploading(false);
        setProgress(0);
        setFile(null);
        if (onUploadSuccess) onUploadSuccess(res);
        onClose();
      }, 700);

    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      setIsUploading(false);
      setError('Error al procesar el archivo. Verifique el formato e intente nuevamente.');
    }
  };

  return (
    <div className="modal-backdrop" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(23, 25, 28, 0.45)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1300,
      padding: '20px'
    }}>
      <div className="modal-panel floating-artifact" style={{
        padding: '32px',
        borderRadius: 'var(--radius-cards)',
        width: '100%',
        maxWidth: '520px',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-modal)',
        position: 'relative'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.9px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
              Ingesta de Datos · Sprint 2
            </span>
            <h3 className="serif-heading" style={{ fontSize: '22px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
              Cargar Nueva Fuente Documental
            </h3>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            type="button"
            style={{ background: 'none', border: 'none', cursor: isUploading ? 'not-allowed' : 'pointer', color: 'var(--color-slate-gray)' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Source selector */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: '8px' }}>
            Selector de Origen Documental
          </label>
          <select
            className="form-input"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            disabled={isUploading}
            style={{ width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-inputs)' }}
          >
            <option>Acta de Calificaciones (Excel)</option>
            <option>Inscripciones (Google Forms)</option>
            <option>Reporte de Aula Virtual (Moodle)</option>
            <option>Cartera de Cobranza (Sheets)</option>
          </select>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
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
            border: dragActive ? '2px dashed var(--color-ink-black)' : '2px dashed var(--color-border)',
            backgroundColor: dragActive ? 'var(--color-mist-gray)' : file ? 'rgba(27, 135, 84, 0.04)' : 'var(--color-fog-white)',
            borderRadius: '18px',
            padding: '30px 20px',
            textAlign: 'center',
            marginBottom: '20px',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          {file ? (
            <div>
              <FileSpreadsheet size={36} color="var(--color-alert-green)" style={{ margin: '0 auto 10px' }} />
              <p style={{ fontSize: '14.5px', fontWeight: 600, color: 'var(--color-ink-black)', margin: 0 }}>
                {file.name}
              </p>
              <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>
                {(file.size / 1024).toFixed(1)} KB — Haga clic para cambiar de archivo
              </p>
            </div>
          ) : (
            <div>
              <UploadCloud size={36} color="var(--color-slate-gray)" style={{ margin: '0 auto 10px' }} />
              <p style={{ fontSize: '14px', color: 'var(--color-ink-black)', margin: 0, fontWeight: 500 }}>
                Arrastra tu archivo aquí o haz clic para explorar
              </p>
              <p style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '6px' }}>
                Compatible con .xlsx, .csv, exportaciones de Moodle y Forms (Máx. 50MB)
              </p>
            </div>
          )}
        </div>

        {/* Progress Bar & Stage Indicator */}
        {isUploading && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
              <span style={{ color: 'var(--color-ink-black)', fontWeight: 500 }}>{stageText}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{progress}%</span>
            </div>
            <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
              <div style={{
                width: `${progress}%`,
                height: '100%',
                backgroundColor: progress === 100 ? 'var(--color-alert-green)' : 'var(--color-ink-black)',
                borderRadius: '9999px',
                transition: 'width 0.4s ease, background-color 0.3s ease'
              }} />
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--color-alert-red)',
            fontSize: '12.5px',
            marginBottom: '16px'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="btn-pill-ghost"
            onClick={onClose}
            disabled={isUploading}
            style={{ padding: '10px 22px', fontSize: '13.5px' }}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn-pill-dark"
            onClick={startUpload}
            disabled={isUploading || !file}
            style={{
              padding: '10px 24px',
              fontSize: '13.5px',
              opacity: isUploading || !file ? 0.6 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {isUploading ? 'Procesando...' : 'Iniciar Carga'}
          </button>
        </div>
      </div>
    </div>
  );
}
