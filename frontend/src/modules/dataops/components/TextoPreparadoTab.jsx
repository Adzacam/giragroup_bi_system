import React, { useEffect, useState } from 'react';
import { AlertTriangle, Eye, EyeOff } from 'lucide-react';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import { FILAS_POR_PAGINA } from '../../../hooks/usePaginacion';
import useTextoPreparado from '../hooks/useTextoPreparado';
import { useRevealCampo } from '../hooks/useRevealCi';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';

export default function TextoPreparadoTab({ batchId, selectedDocId, context }) {
  const filterKey = `${batchId}:${selectedDocId}`;
  const [pagination, setPagination] = useState(null);
  const page = pagination?.key === filterKey ? pagination.page : 1;
  const { data, error, isFetching, isPending, refetch } = useTextoPreparado(batchId, selectedDocId, page, !!context);
  const { toggleCampo, getValor } = useRevealCampo();
  const [loadingCampo, setLoadingCampo] = useState(null);

  const handleReveal = async (rowId, campo) => {
    const key = `${rowId}:${campo}`;
    setLoadingCampo(key);
    try {
      await toggleCampo(rowId, campo);
    } finally {
      setLoadingCampo(null);
    }
  };

  const rows = data?.registros || [];
  const total = data?.total ?? 0;
  const pageCount = data?.total_pages ?? 1;

  useEffect(() => {
    if (error) {
      sileoToast.error({
        title: 'No se pudo cargar el texto',
        description: mensajeError(error, 'Pulsa Reintentar para volver a consultar el lote.'),
      });
    }
  }, [error]);

  useEffect(() => {
    if (data && page > pageCount) {
      setPagination({ key: filterKey, page: pageCount });
    }
  }, [data, page, pageCount, filterKey]);

  const refresh = async () => {
    const result = await refetch();
    if (!result.error) {
      sileoToast.success({ title: 'Texto actualizado', description: 'Se volvió a consultar la página seleccionada.' });
    }
  };

  return (
    <>
      <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: 18 }}>Del archivo al texto</h3>
            <p style={{ color: 'var(--color-slate-gray)', fontSize: 13, marginTop: 6 }}>
              Compara cada fila con el texto que leerá BETO. Los nombres, documentos y datos de contacto se muestran protegidos.
            </p>
          </div>
          <Button variant="ghost" onClick={refresh} disabled={!context} isLoading={isFetching} loadingText="Actualizando…">
            Actualizar
          </Button>
        </div>
      </div>

      {error ? (
        <div className="floating-artifact" role="alert" style={{ padding: 24 }}>
          <p>No se pudo cargar la página. El lote conserva sus datos.</p>
          <Button variant="ghost" onClick={refresh} isLoading={isFetching} loadingText="Reintentando…" style={{ marginTop: 12 }}>
            Reintentar
          </Button>
        </div>
      ) : isPending || isFetching ? (
        <div className="floating-artifact" role="status" aria-live="polite" style={{ padding: 32 }}>
          Cargando página {page}…
        </div>
      ) : (
        <>
          <div className="floating-artifact" style={{ padding: 24 }} aria-busy={isFetching}>
            <div style={{ overflowX: 'auto' }}>
              <table className="dataops-table" style={{ width: '100%', textAlign: 'left', tableLayout: 'fixed' }}>
                <thead>
                  <tr>
                    <th style={{ width: 70 }}>Fila</th>
                    <th>Contenido del archivo</th>
                    <th>Texto para BETO</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const rowId = `REG_${row.stg_id}_${row.line_number}`;
                    const nombreRev = getValor(rowId, 'nombre');
                    const correoRev = getValor(rowId, 'correo');
                    const hasCorreo = Boolean(
                      correoRev ||
                      row.tiene_correo ||
                      (row.correo_enmascarado && !['No provisto', 'No especificado', 'Sin dato'].includes(row.correo_enmascarado)) ||
                      (row.oracion_beto && row.oracion_beto.includes('@')) ||
                      (Array.isArray(row.fila_original) && row.fila_original.some((c) => String(c).includes('@')))
                    );
                    return (
                    <tr key={`${row.stg_id}:${row.line_number}`}>
                      <td>{row.line_number}</td>
                      <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
                        <small style={{ color: 'var(--color-slate-gray)' }}>{row.nombre_archivo}</small>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                          <Button
                            variant="ghost"
                            type="button"
                            isLoading={loadingCampo === `${rowId}:nombre`}
                            loadingText="Consultando…"
                            aria-label={nombreRev ? 'Ocultar nombre' : 'Revelar nombre con auditoría'}
                            onClick={() => handleReveal(rowId, 'nombre')}
                            style={{ padding: '3px 8px', fontSize: 11 }}
                          >
                            {nombreRev ? <EyeOff size={12} /> : <Eye size={12} />} {nombreRev ? `Nombre: ${nombreRev}` : 'Revelar nombre'}
                          </Button>
                          {hasCorreo && (
                            <Button
                              variant="ghost"
                              type="button"
                              isLoading={loadingCampo === `${rowId}:correo`}
                              loadingText="Consultando…"
                              aria-label={correoRev ? 'Ocultar correo' : 'Revelar correo con auditoría'}
                              onClick={() => handleReveal(rowId, 'correo')}
                              style={{ padding: '3px 8px', fontSize: 11 }}
                            >
                              {correoRev ? <EyeOff size={12} /> : <Eye size={12} />} {correoRev ? `Correo: ${correoRev}` : 'Revelar correo'}
                            </Button>
                          )}
                        </div>
                        <details style={{ marginTop: 6 }}>
                          <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>
                            Ver campos ({row.fila_original?.length || 0})
                          </summary>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                            {(row.fila_original || []).map((cell, index) => (
                              <span key={index} className="chip-cat" style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                                {cell}
                              </span>
                            ))}
                          </div>
                        </details>
                      </td>
                      <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
                        <p>{row.oracion_beto?.length > 300 ? `${row.oracion_beto.slice(0, 300)}…` : row.oracion_beto || 'Sin dato'}</p>
                        {row.oracion_beto?.length > 300 && (
                          <details style={{ marginTop: 8 }}>
                            <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Ver texto completo</summary>
                            <p style={{ marginTop: 8 }}>{row.oracion_beto}</p>
                          </details>
                        )}
                        {row.alerta && (
                          <p style={{ color: 'var(--dataops-warning-text)', marginTop: 8, fontSize: 12 }}>
                            <AlertTriangle size={13} aria-hidden="true" /> {row.alerta}
                          </p>
                        )}
                        {row.vista_abreviada && (
                          <p style={{ color: 'var(--color-slate-gray)', marginTop: 8, fontSize: 12 }}>
                            Vista abreviada de una fila extensa.
                          </p>
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
              {rows.length === 0 && (
                <p role="status" style={{ padding: '20px 0' }}>
                  No hay registros preparados para esta selección.
                </p>
              )}
            </div>
            <Paginacion
              pagina={page}
              totalPaginas={pageCount}
              total={total}
              filasPorPagina={FILAS_POR_PAGINA}
              disabled={isFetching}
              onChange={(next) => setPagination({ key: filterKey, page: next })}
            />
          </div>

          {!!data?.diagnosticos?.length && (
            <details className="floating-artifact" style={{ padding: 20, marginTop: 20 }}>
              <summary style={{ cursor: 'pointer' }}>Detalles de preparación</summary>
              {data.diagnosticos.map((diag) => (
                <p key={diag.id_documento} style={{ marginTop: 12, fontSize: 12, color: 'var(--color-slate-gray)' }}>
                  {context?.archivos?.find((a) => a.id_documento === diag.id_documento)?.nombre_archivo || 'Archivo'} · Fila de encabezados: {diag.fila_cabecera ?? 'Sin dato'} · Subtotales descartados: {diag.filas_subtotales_descartadas ?? 'Sin dato'}
                </p>
              ))}
            </details>
          )}
        </>
      )}
    </>
  );
}
