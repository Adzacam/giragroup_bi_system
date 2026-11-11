import React, { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import { confirmar, sileoToast } from '../../../services/sileoToast';
import { avisarTareaIniciada } from '../../../components/shared/TareasSegundoPlano';
import { mensajeError } from '../../../utils/mensajeError';
import { TIPOS_FUENTE_DATAOPS } from '../../../constants/dataopsConfig';

const ESTADOS = {
  CARGADO: ['Cargado', ['texto', 'beto']],
  TEXTO_LISTO: ['Texto listo', ['beto']],
  LEIDO_BETO: ['Leído por BETO', ['revision']],
  EN_REVISION: ['En revisión', ['revision']],
  CONSOLIDADO: ['Consolidado', []],
  ERROR: ['Con error', []],
};
const PASOS = { texto: '② Texto', beto: '③ BETO', revision: '④ Revisión' };

export default function BatchHistory({ onInspect, onLogs, onNewBatch, loadingLogs, inspecting, disabled }) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(null);
  const busyRef = useRef(false);
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'historial', page],
    queryFn: () => dataopsApi.getBatchHistory(page),
  });
  const rows = data?.data || [];
  const total = data?.total ?? 0;
  const mutate = async (src, action) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(src.id_lote);
    try {
      if (action === 'delete') {
        if (!await confirmar({ title: `Eliminar lote #${src.id_lote}`, description: 'Este lote falló y no contiene archivos procesados. Se eliminará su entrada del historial.', confirmText: 'Eliminar lote' })) return;
        await dataopsApi.deleteFailedBatch(src.id_lote);
        if (rows.length === 1 && page > 1) setPage(page - 1);
      } else {
        await dataopsApi.retryBatchReading(src.id_lote);
        avisarTareaIniciada();
      }
      sileoToast.success({ title: action === 'delete' ? 'Lote eliminado' : 'Lectura reanudada', description: action === 'delete' ? 'El historial se ha actualizado.' : 'Puedes seguir el avance desde las notificaciones.' });
      await refetch();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo completar la acción', description: mensajeError(err, 'Inténtalo de nuevo.') });
    } finally { busyRef.current = false; setBusy(null); }
  };
  const locked = disabled || !!busy || inspecting;
  return (
    <details className="floating-artifact" style={{ padding: '20px 24px' }}>
      <summary style={{ cursor: 'pointer', color: 'var(--color-ink-black)' }}>Historial de lotes ({total})</summary>
      <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '12px 0' }}>
        <Button variant="ghost" onClick={() => refetch()} isLoading={isFetching} loadingText="Actualizando…">Actualizar</Button>
      </div>
      {error ? <p role="alert">No se pudo cargar el historial. Pulsa Actualizar para reintentarlo.</p> : !data ? <p role="status">Cargando historial…</p> : rows.length === 0 ? <p>No hay lotes registrados.</p> : (
        <div style={{ overflowX: 'auto' }}>
          <table className="dataops-table" style={{ width: '100%', textAlign: 'left' }}>
            <thead><tr>{['Lote / Archivo', 'Origen', 'Registros', 'Fecha de carga', 'Estado', 'Acciones'].map(t => <th key={t}>{t}</th>)}</tr></thead>
            <tbody>{rows.map(src => {
              const [label, steps] = ESTADOS[src.status] || ['Sin dato', []];
              const source = src.total_archivos > 1 && !src.tipo_fuente ? 'Varios orígenes' : TIPOS_FUENTE_DATAOPS.find(t => t.code === src.tipo_fuente)?.label || 'Sin dato';
              const date = src.date ? new Date(src.date) : null;
              return <tr key={src.id_lote}>
                <td>{src.name === `Lote #${src.id_lote}` ? src.name : `Lote #${src.id_lote} · ${src.name || 'Sin dato'}`}<br /><small>{src.total_archivos} archivo(s)</small></td>
                <td>{source}</td><td>{src.records ?? 'Sin dato'}</td>
                <td>{date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('es-BO') : 'Sin dato'}</td><td>{label}</td>
                <td><div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {src.id_documento && steps.map(step => <Button key={step} disabled={locked} variant="ghost" onClick={() => navigate(`/dataops/lote/${src.id_lote}/${step}`)}>{PASOS[step]}</Button>)}
                  {src.status === 'CONSOLIDADO' && <>
                    <Button variant="ghost" disabled={locked} onClick={() => navigate(`/dataops/lote/${src.id_lote}/revision`)}>Ver resumen</Button>
                    <Button variant="ghost" disabled={locked} onClick={onNewBatch}>Iniciar nuevo lote</Button>
                  </>}
                  {src.status === 'ERROR' && <>
                    <Button variant="ghost" disabled={locked} isLoading={busy === src.id_lote} onClick={() => src.puede_reintentar_lectura ? mutate(src, 'retry') : onNewBatch()}>Reintentar {src.puede_reintentar_lectura ? 'lectura' : 'carga'}</Button>
                    {src.puede_eliminar && <Button variant="ghost" disabled={locked} onClick={() => mutate(src, 'delete')}>Eliminar</Button>}
                  </>}
                  {!['CONSOLIDADO', 'ERROR'].includes(src.status) && src.id_documento && <Button variant="ghost" disabled={locked} isLoading={inspecting} onClick={() => onInspect(src)}>Inspeccionar</Button>}
                  {src.id_documento && <Button variant="ghost" isLoading={loadingLogs === src.id_documento} disabled={!!loadingLogs || locked} onClick={() => onLogs(src)}>Bitácora</Button>}
                </div></td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      )}
      <Paginacion pagina={page} totalPaginas={Math.max(1, Math.ceil(total / 5))} total={total} filasPorPagina={5} onChange={setPage} />
    </details>
  );
}
