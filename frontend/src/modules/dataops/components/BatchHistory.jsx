import React, { useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import { confirmar, sileoToast } from '../../../services/sileoToast';
import { avisarTareaIniciada } from '../../../components/shared/TareasSegundoPlano';
import { mensajeError } from '../../../utils/mensajeError';
import { getTipoFuenteLabel } from '../../../constants/dataopsConfig';
import AnimatedNumberV2 from '../../../v2/motion/AnimatedNumberV2';
import { toDataopsPath } from '../../../v2/utils/v2Routes';
import {
  getAccionesBloqueHabilitadas,
  isAllBatchesSelected,
  toggleBatchSelection,
  toggleSelectAllBatches,
} from '../utils/cargaHistorialHelpers';

const ESTADOS = {
  CARGADO: ['Cargado', ['beto']],
  TEXTO_LISTO: ['Texto listo', ['beto']],
  LEIDO_BETO: ['Leído por BETO', ['revision']],
  EN_REVISION: ['En revisión', ['revision']],
  CONSOLIDADO: ['Consolidado', []],
  ERROR: ['Con error', []],
};
const PASOS = { beto: '② Lectura de BETO', revision: '③ Revisión' };

export default function BatchHistory({ onInspect, onLogs, onNewBatch, loadingLogs, inspecting, disabled }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const busyRef = useRef(false);
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'historial', page],
    queryFn: () => dataopsApi.getBatchHistory(page),
  });
  const rows = data?.data || [];
  const total = data?.total ?? 0;

  const selectedBatches = useMemo(() => {
    const set = new Set(selectedIds);
    return rows.filter((r) => set.has(r.id_lote));
  }, [rows, selectedIds]);

  const bulkEligibility = useMemo(
    () => getAccionesBloqueHabilitadas(selectedBatches),
    [selectedBatches]
  );

  const allSelected = isAllBatchesSelected(rows, selectedIds);

  const handlePageChange = (nextPage) => {
    setSelectedIds([]);
    setPage(nextPage);
  };

  const mutate = async (src, action) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy({ id: src.id_lote, action });
    try {
      if (action === 'delete') {
        if (!await confirmar({ title: `Eliminar lote #${src.id_lote}`, description: 'Este lote falló y no contiene archivos procesados. Se eliminará su entrada del historial.', confirmText: 'Eliminar lote' })) return;
        await dataopsApi.deleteFailedBatch(src.id_lote);
        setSelectedIds((prev) => prev.filter((id) => id !== src.id_lote));
        if (rows.length === 1 && page > 1) setPage(page - 1);
      } else if (action === 'reset') {
        if (!await confirmar({ title: `Reiniciar lote #${src.id_lote}`, description: 'Se eliminará este lote y sus archivos cargados en staging para que puedas volver a subir los archivos correctos.', confirmText: 'Reiniciar lote' })) return;
        await dataopsApi.reiniciarLote(src.id_lote);
        if (localStorage.getItem('last_active_batch_id') === String(src.id_lote)) {
          onNewBatch?.();
        }
        setSelectedIds((prev) => prev.filter((id) => id !== src.id_lote));
        if (rows.length === 1 && page > 1) setPage(page - 1);
      } else {
        await dataopsApi.retryBatchReading(src.id_lote);
        avisarTareaIniciada();
      }
      const msgTitle = action === 'delete' ? 'Lote eliminado' : action === 'reset' ? 'Lote reiniciado' : 'Lectura reanudada';
      const msgDesc = action === 'retry' ? 'Puedes seguir el avance desde las notificaciones.' : 'El historial se ha actualizado.';
      sileoToast.success({ title: msgTitle, description: msgDesc });
      await refetch();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo completar la acción', description: mensajeError(err, 'Inténtalo de nuevo.') });
    } finally { busyRef.current = false; setBusy(null); }
  };

  const handleBulkAction = async (action) => {
    if (busyRef.current || selectedBatches.length === 0) return;
    if (action === 'delete' && !bulkEligibility.canDelete) return;
    if (action === 'retry' && !bulkEligibility.canRetry) return;

    const count = selectedBatches.length;
    busyRef.current = true;
    setBusy({ id: 'bulk', action: action === 'delete' ? 'bulk-delete' : 'bulk-retry' });
    try {
      const confirmed = await confirmar(
        action === 'delete'
          ? {
              title: `Eliminar ${count} lote(s)`,
              description: 'Los lotes seleccionados fallaron y no contienen archivos procesados. Se eliminarán del historial.',
              confirmText: `Eliminar ${count} lote(s)`,
            }
          : {
              title: `Reintentar lectura de ${count} lote(s)`,
              description: 'Se volverá a iniciar la lectura en segundo plano para los lotes seleccionados.',
              confirmText: `Reintentar ${count} lote(s)`,
            }
      );
      if (!confirmed) return;

      let exitos = 0;
      let fallos = 0;
      for (const src of selectedBatches) {
        try {
          if (action === 'delete') {
            await dataopsApi.deleteFailedBatch(src.id_lote);
          } else {
            await dataopsApi.retryBatchReading(src.id_lote);
          }
          exitos += 1;
        } catch {
          fallos += 1;
        }
      }

      if (exitos > 0) {
        if (action === 'delete') {
          sileoToast.bulkDeleteSummary(exitos, { entity: 'lote', plural: 'lotes' });
          if (exitos >= rows.length && page > 1) setPage(page - 1);
        } else {
          avisarTareaIniciada();
          sileoToast.success({
            title: exitos === 1 ? 'Lectura reanudada' : `Lectura reanudada (${exitos} lotes)`,
            description: 'Puedes seguir el avance desde las notificaciones.',
          });
        }
      }
      if (fallos > 0) {
        sileoToast.error({
          title: `${fallos} lote(s) no se pudieron procesar`,
          description: 'Revisa el historial e inténtalo de nuevo.',
        });
      }
      setSelectedIds([]);
      await refetch();
    } finally {
      busyRef.current = false;
      setBusy(null);
    }
  };

  const locked = disabled || !!busy || inspecting;
  return (
    <details className="floating-artifact" style={{ padding: '20px 24px' }}>
      <summary style={{ cursor: 'pointer', color: 'var(--color-ink-black)' }}>Historial de lotes ({Number(total || 0).toLocaleString('es-BO')})</summary>
      <div className="dataops-bulk-bar">
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
          {selectedBatches.length > 0 && (
            <>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink-black)' }}>
                {selectedBatches.length} seleccionado(s)
              </span>
              {bulkEligibility.canRetry && (
                <Button
                  variant="ghost"
                  disabled={locked}
                  isLoading={busy?.action === 'bulk-retry'}
                  loadingText="Procesando…"
                  onClick={() => handleBulkAction('retry')}
                >
                  Reintentar seleccionados ({selectedBatches.length})
                </Button>
              )}
              {bulkEligibility.canDelete && (
                <Button
                  variant="ghost"
                  disabled={locked}
                  isLoading={busy?.action === 'bulk-delete'}
                  loadingText="Procesando…"
                  onClick={() => handleBulkAction('delete')}
                >
                  Eliminar seleccionados ({selectedBatches.length})
                </Button>
              )}
              {!bulkEligibility.canRetry && !bulkEligibility.canDelete && (
                <span style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>
                  El estado de los lotes seleccionados no permite acciones en bloque.
                </span>
              )}
            </>
          )}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 8 }}>
          <Button variant="ghost" disabled={locked} onClick={onNewBatch}>Iniciar nuevo lote</Button>
          <Button variant="ghost" onClick={() => refetch()} isLoading={isFetching} loadingText="Procesando…">Actualizar</Button>
        </div>
      </div>
      {error ? <p role="alert">No se pudo cargar el historial. Pulsa Actualizar para reintentarlo.</p> : !data ? <p role="status">Cargando historial…</p> : rows.length === 0 ? <p>No hay lotes registrados.</p> : (
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table className="dataops-table" style={{ width: '100%', textAlign: 'left' }}>
            <thead>
              <tr>
                <th style={{ width: 36 }}>
                  <input
                    type="checkbox"
                    aria-label="Seleccionar todo"
                    checked={allSelected}
                    disabled={locked || rows.length === 0}
                    onChange={() => setSelectedIds((prev) => toggleSelectAllBatches(rows, prev))}
                  />
                </th>
                {['Lote / Archivo', 'Origen', 'Registros', 'Fecha de carga', 'Estado', 'Acciones'].map(t => <th key={t}>{t}</th>)}
              </tr>
            </thead>
            <tbody>{rows.map(src => {
              const [label, steps] = ESTADOS[src.status] || ['Sin dato', []];
              const source = src.total_archivos > 1 && !src.tipo_fuente ? 'Varios orígenes' : getTipoFuenteLabel(src.tipo_fuente) || src.tipo_fuente || 'Sin dato';
              const date = src.date ? new Date(src.date) : null;
              const isChecked = selectedIds.includes(src.id_lote);
              return (
                <tr key={src.id_lote} className={`dataops-table-row ${isChecked ? 'selected' : ''}`} style={{ cursor: 'default' }}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Seleccionar lote #${src.id_lote}`}
                      checked={isChecked}
                      disabled={locked}
                      onChange={() => setSelectedIds((prev) => toggleBatchSelection(prev, src.id_lote))}
                    />
                  </td>
                  <td>{`Lote #${src.id_lote} · ${source}${src.periodo ? ` · ${src.periodo}` : ''}`}<br /><small>{src.name && src.name !== `Lote #${src.id_lote}` ? `${src.name} · ` : ''}{src.total_archivos} archivo(s)</small></td>
                  <td>{source}</td><td>{src.records != null ? Number(src.records).toLocaleString('es-BO') : 'Sin dato'}</td>
                  <td>{date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('es-BO') : 'Sin dato'}</td><td>{label}</td>
                  <td><div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {src.id_documento && steps.map(step => <Button key={step} disabled={locked} variant="ghost" onClick={() => navigate(toDataopsPath(`/lote/${src.id_lote}/${step}`, location.pathname))}>{PASOS[step]}</Button>)}
                    {src.status === 'CONSOLIDADO' && <>
                      <Button variant="ghost" disabled={locked} onClick={() => navigate(toDataopsPath(`/lote/${src.id_lote}/revision`, location.pathname))}>Ver resumen</Button>
                    </>}
                    {src.status === 'ERROR' && <>
                      <Button variant="ghost" disabled={locked} isLoading={busy?.id === src.id_lote && busy?.action === 'retry'} onClick={() => src.puede_reintentar_lectura ? mutate(src, 'retry') : onNewBatch()}>Reintentar {src.puede_reintentar_lectura ? 'lectura' : 'carga'}</Button>
                      {src.puede_eliminar && <Button variant="ghost" disabled={locked} isLoading={busy?.id === src.id_lote && busy?.action === 'delete'} onClick={() => mutate(src, 'delete')}>Eliminar</Button>}
                    </>}
                    {!['CONSOLIDADO', 'ERROR'].includes(src.status) && src.id_documento && <Button variant="ghost" disabled={locked} isLoading={inspecting} onClick={() => onInspect(src)}>Inspeccionar</Button>}
                    {src.status !== 'CONSOLIDADO' && !src.puede_eliminar && (
                      <Button
                        variant="ghost"
                        className="dataops-btn-danger"
                        disabled={locked}
                        isLoading={busy?.id === src.id_lote && busy?.action === 'reset'}
                        onClick={() => mutate(src, 'reset')}
                      >
                        Reiniciar
                      </Button>
                    )}
                    {src.id_documento && <Button variant="ghost" isLoading={loadingLogs === src.id_documento} disabled={!!loadingLogs || locked} onClick={() => onLogs(src)}>Bitácora</Button>}
                  </div></td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      )}
      <Paginacion pagina={page} totalPaginas={Math.max(1, Math.ceil(total / 5))} total={total} filasPorPagina={5} onChange={handlePageChange} />
    </details>
  );
}
