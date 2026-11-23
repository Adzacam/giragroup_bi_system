import React from 'react';
import { UploadCloud, Play, XCircle } from 'lucide-react';
import Button from '../../../components/shared/Button';
import { MAX_ARCHIVOS_POR_LOTE, MAX_TAMANO_ARCHIVO_MB } from '../../../constants/dataopsConfig';

export default function IngestDropzonePanel({
  dropzoneRef,
  isDragging,
  setIsDragging,
  isProcessing,
  isCheckingFiles,
  uploadProgress,
  isFormValid,
  queuedFiles,
  selectedQueueFiles,
  onDrop,
  onFileSelect,
  onProcessBatch,
  onClearQueue,
  onCancelUpload,
}) {
  return (
    <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
          Cargar archivos
        </h2>
        <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
          Puedes cargar archivos de <strong>Exportaciones Moodle, Google Sheets</strong> (Actas Notas/Asistencia), <strong>Google Forms</strong> (Admisiones/Pagos). Hasta {MAX_ARCHIVOS_POR_LOTE} archivos .xlsx o .csv, de {MAX_TAMANO_ARCHIVO_MB} MB cada uno.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <span className="chip-cat chip-origen">Moodle Export (.csv / .xlsx)</span>
        <span className="chip-cat chip-origen">Google Sheets (Actas Notas / Asist)</span>
        <span className="chip-cat chip-origen">Google Forms (Admisiones / Pagos)</span>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
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
          transition: 'border-color 0.2s ease, background-color 0.2s ease',
        }}
        role="button"
        ref={dropzoneRef}
        tabIndex={isProcessing || isCheckingFiles ? -1 : 0}
        aria-label="Seleccionar archivos"
        aria-disabled={isProcessing || isCheckingFiles}
        onKeyDown={(e) => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); if (!isProcessing && !isCheckingFiles) document.getElementById('file-upload-input').click(); } }}
        onClick={() => { if (!isProcessing && !isCheckingFiles) document.getElementById('file-upload-input').click(); }}
      >
        <input id="file-upload-input" type="file" multiple disabled={isProcessing || isCheckingFiles} accept=".xlsx,.csv" style={{ display: 'none' }} onChange={onFileSelect} />
        <div style={{ width: '44px', height: '44px', borderRadius: '50%', backgroundColor: 'var(--dataops-gold-bg)', color: 'var(--color-gira-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <UploadCloud size={22} />
        </div>
        <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-ink-black)', fontFamily: 'var(--font-sohne)' }}>
          Arrastra archivos .XLSX o .CSV aquí
        </div>
        <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
          {isCheckingFiles ? 'Revisando archivos…' : 'o haz clic para seleccionarlos desde tu equipo'}
        </div>
      </div>

      <div className="dataops-queue-actions">
        <Button
          variant="ghost"
          onClick={onProcessBatch}
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
          onClick={onClearQueue}
          style={{
            padding: '8px 14px',
            fontSize: '12px',
            borderRadius: '8px',
            backgroundColor: 'var(--color-mist-gray)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-ink-black)',
            opacity: queuedFiles.length === 0 || isProcessing || isCheckingFiles ? 0.78 : 1,
            fontWeight: 600,
          }}
        >
          Vaciar cola ({queuedFiles.length})
        </Button>

        {isProcessing && onCancelUpload && (
          <Button
            variant="ghost"
            className="dataops-btn-danger"
            onClick={onCancelUpload}
            style={{
              padding: '8px 14px',
              fontSize: '12px',
              borderRadius: '8px',
              fontWeight: 600,
            }}
          >
            <XCircle size={14} /> Cancelar carga
          </Button>
        )}
      </div>
    </div>
  );
}
