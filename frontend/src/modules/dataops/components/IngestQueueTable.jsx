import React from 'react';
import { FileSpreadsheet, ShieldCheck, Trash2 } from 'lucide-react';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import { formatFileSize, isAcademicSourceType, toCanonicalSourceCode, UNRECOGNIZED_SOURCE_LABEL } from '../../../utils/fileTypeDetector';
import { ESCALAS_ACADEMICAS, TIPOS_FUENTE_DATAOPS, getTipoFuenteLabel } from '../../../constants/dataopsConfig';
import { toggleSelectAllQueue, toggleUidSelection } from '../utils/cargaHistorialHelpers';

export default function IngestQueueTable({
  queuedFiles,
  queuePagination,
  selectedQueueUids,
  setSelectedQueueUids,
  allQueueSelected,
  expandedDetailKey,
  isProcessing,
  isCheckingFiles,
  onChangeFileSourceType,
  onChangeFileScale,
  onTogglePreview,
  onRemoveFile,
}) {
  return (
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
              <tr key={item.uid} className={`dataops-table-row ${isSelected ? 'selected' : ''}`} style={{ cursor: 'default' }}>
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
                    onChange={(e) => onChangeFileSourceType(item.uid, e.target.value)}
                    className="dataops-select"
                    style={{ padding: '4px 8px', fontSize: '11.5px', minWidth: '150px', backgroundColor: 'var(--color-paper-white)', color: 'var(--color-ink-black)' }}
                  >
                    <option value="">{UNRECOGNIZED_SOURCE_LABEL}</option>
                    {TIPOS_FUENTE_DATAOPS.map((tf) => <option key={tf.code} value={tf.code}>{tf.label}</option>)}
                  </select>
                </td>
                <td>
                  {isAcademic ? (
                    <select
                      value={item.tipoEscala || ''}
                      aria-label={`Escala de notas de ${item.file.name}`}
                      disabled={isProcessing}
                      onChange={(e) => onChangeFileScale(item.uid, e.target.value)}
                      className="dataops-select"
                      style={{ padding: '4px 8px', fontSize: '11.5px', minWidth: '150px', backgroundColor: 'var(--color-paper-white)', color: 'var(--color-ink-black)' }}
                    >
                      <option value="">Selecciona la escala de notas</option>
                      {ESCALAS_ACADEMICAS.map((esc) => <option key={esc.value} value={esc.value}>{esc.label}</option>)}
                    </select>
                  ) : isEvalDocente ? (
                    <div role="note" style={{ fontSize: '11px', color: 'var(--color-slate-gray)', padding: '4px 8px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                      Escala de respuesta: 1 a 5 / 1 a 10 (detectada)
                    </div>
                  ) : (
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>No aplica</span>
                  )}
                </td>
                <td>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700, color: 'var(--color-alert-green)', backgroundColor: 'var(--dataops-success-bg)', padding: '2px 8px', borderRadius: '4px' }}>
                    <ShieldCheck size={12} /> Se protege al procesar
                  </span>
                </td>
                <td><span className="chip-cat chip-fecha">[{item.status}]</span></td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <Button variant="ghost" type="button" onClick={() => onTogglePreview(item)} style={{ padding: '4px 8px', fontSize: '11px' }}>
                      {isExpanded ? 'Ocultar' : 'Vista previa'}
                    </Button>
                    <Button variant="ghost" type="button" onClick={() => onRemoveFile(item.uid)} disabled={isProcessing || isCheckingFiles} aria-label={`Quitar ${item.file.name}`} title="Quitar archivo" style={{ padding: '4px 8px' }}>
                      <Trash2 size={13} />
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <Paginacion {...queuePagination} onChange={queuePagination.setPagina} />
    </div>
  );
}
