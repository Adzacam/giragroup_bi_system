import React from 'react';
import Button from '../../../components/shared/Button';
import { formatFileSize } from '../../../utils/fileTypeDetector';
import { getTipoFuenteLabel } from '../../../constants/dataopsConfig';

export default function IngestWorkbookPreview({ previewItem, previewData, loading, onClose, onChangeColumnMapping }) {
  if (!previewItem) return null;
  const previewTipoLabel = getTipoFuenteLabel(previewItem.sourceType) || 'Por seleccionar';
  const previewFileSize = formatFileSize(previewItem.file.size);

  return (
    <section
      aria-label={`Vista previa de ${previewItem.file.name}`}
      style={{
        marginTop: 16,
        borderRadius: '10px',
        border: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-alabaster)',
        overflow: 'hidden',
      }}
    >
      <div className="dataops-row-detail" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, alignItems: 'center' }}>
          <span><strong>Archivo:</strong> {previewItem.file.name}</span>
          <span><strong>Tamaño:</strong> {previewFileSize}</span>
          <span><strong>Origen:</strong> {previewTipoLabel}</span>
          <span><strong>Fechas:</strong> Por detectar al procesar</span>
          <span><strong>Estado:</strong> {previewItem.status}</span>
        </div>
        <Button variant="ghost" type="button" onClick={onClose} style={{ padding: '4px 10px', fontSize: '11px' }}>
          Ocultar vista previa
        </Button>
      </div>
      <div style={{ padding: '14px 16px', borderTop: '1px solid var(--color-border)' }}>
        {loading ? (
          <p role="status" style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>Analizando hojas y encabezados del libro…</p>
        ) : previewData ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', fontSize: 12 }}>
              {previewData.tipo_fuente && (
                <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', fontWeight: 600 }}>
                  Detectado: {getTipoFuenteLabel(previewData.tipo_fuente) || previewData.tipo_fuente}
                  {previewData.confianza != null ? ` (${Math.round(Number(previewData.confianza) * 100)} %)` : ''}
                </span>
              )}
              {Array.isArray(previewData.senales) && previewData.senales.slice(0, 3).map((s, idx) => (
                <span key={idx} style={{ padding: '2px 8px', borderRadius: 999, backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)', fontSize: 11 }}>
                  {String(s)}
                </span>
              ))}
              <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-ink-black)' }}>
                Hojas totales: <strong>{previewData.resumen_hojas?.total ?? 0}</strong>
              </span>
              <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)' }}>
                Usadas: <strong>{previewData.resumen_hojas?.usadas ?? 0}</strong>
              </span>
              <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)' }}>
                Ignoradas: <strong>{previewData.resumen_hojas?.ignoradas ?? 0}</strong>
              </span>
              <span style={{ padding: '2px 10px', borderRadius: 999, backgroundColor: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                Ocultas: <strong>{previewData.resumen_hojas?.ocultas ?? 0}</strong>
              </span>
            </div>
            <div tabIndex={0} role="region" aria-label={`Hojas de ${previewItem.file.name}`} style={{ overflowX: 'auto' }}>
              <table className="dataops-table" style={{ width: '100%', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th scope="col">Hoja</th><th scope="col">Visibilidad</th><th scope="col">Decisión</th><th scope="col">Motivo</th><th scope="col">Filas estimadas</th>
                  </tr>
                </thead>
                <tbody>
                  {(previewData.hojas || []).map((h) => (
                    <tr key={h.hoja}>
                      <td><strong>{h.hoja}</strong></td>
                      <td>{h.estado_visibilidad}</td>
                      <td>
                        <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600, backgroundColor: h.decision === 'usada' ? 'var(--dataops-success-bg)' : 'var(--dataops-warning-bg)', color: h.decision === 'usada' ? 'var(--dataops-success-text)' : 'var(--dataops-warning-text)' }}>
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
            {previewData.mapeo_columnas?.length > 0 && (
              <div tabIndex={0} role="region" aria-label={`Mapeo de columnas de ${previewItem.file.name}`} style={{ overflowX: 'auto' }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: 6 }}>Mapeo editable columna → campo canónico</p>
                <table className="dataops-table" style={{ width: '100%', fontSize: 12 }}>
                  <thead><tr><th scope="col">Columna del archivo</th><th scope="col">Hoja</th><th scope="col">Campo canónico</th></tr></thead>
                  <tbody>
                    {previewData.mapeo_columnas.map((m) => (
                      <tr key={`${m.hoja}-${m.columna_origen}`}>
                        <td>{m.columna_origen}</td>
                        <td style={{ color: 'var(--color-slate-gray)' }}>{m.hoja}</td>
                        <td>
                          <select
                            className="dataops-select"
                            aria-label={`Campo canónico para ${m.columna_origen}`}
                            value={m.campo_canonico || ''}
                            onChange={(e) => onChangeColumnMapping(previewItem.uid, m.columna_origen, e.target.value)}
                            style={{ padding: '4px 8px', fontSize: 11.5, backgroundColor: 'var(--color-paper-white)', color: 'var(--color-ink-black)' }}
                          >
                            <option value="">Sin asignar…</option>
                            {(previewData.campos_canonicos_disponibles || []).map((c) => <option key={c} value={c}>{c}</option>)}
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
    </section>
  );
}
