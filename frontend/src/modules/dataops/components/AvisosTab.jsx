import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY, queryClient } from '../../../api/queryClient';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';
import ReviewActionRenderer from './ReviewActionRenderer';

export default function AvisosTab({ batchId, docId = null, readOnly = false }) {
  const [busy, setBusy] = useState(false);
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'review-avisos', String(batchId || ''), docId || ''],
    queryFn: () => dataopsApi.getReviewTrayAvisos(batchId, docId, 'PENDIENTE'),
  });

  const handleExecute = async (aviso, accion, form) => {
    setBusy(true);
    try {
      await dataopsApi.resolveReviewAviso(aviso.id, { accion: accion.codigo, ...form });
      sileoToast.success({ title: 'Aviso resuelto', description: 'La inconsistencia quedó atendida y auditada.' });
      await refetch();
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    } catch (err) {
      sileoToast.error({ title: 'No se pudo resolver el aviso', description: mensajeError(err) });
    } finally {
      setBusy(false);
    }
  };

  if (isFetching && !data) return <p role="status">Consultando avisos de inconsistencias…</p>;
  if (error) return <p role="alert">No se pudieron consultar los avisos.</p>;
  const items = data?.items || [];
  if (!items.length) return <p role="status">No hay avisos pendientes en este lote.</p>;

  return (
    <div style={{ display: 'grid', gap: 14, minWidth: 0 }}>
      <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>
        Avisos registrados en bitácora de inconsistencias ({items.length}).
      </p>
      {items.map((aviso) => (
        <div key={aviso.id} style={{ padding: 14, borderRadius: 12, border: '1px solid var(--color-border)', minWidth: 0, overflowWrap: 'anywhere' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, minWidth: 0 }}>
            <strong style={{ minWidth: 0, maxWidth: '100%', overflowWrap: 'anywhere', wordBreak: 'break-word' }}>{aviso.tipo_regla}</strong>
            <span style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', minWidth: 0, overflowWrap: 'anywhere', wordBreak: 'break-word' }}>
              Fila {aviso.fila_origen ?? '—'} · Campo: {aviso.campo_afectado || '—'} · Severidad: {aviso.severidad || 'MEDIA'}
            </span>
          </div>
          {aviso.valor_recibido && (
            <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginTop: 6, overflowWrap: 'anywhere', wordBreak: 'break-word' }}>Valor recibido: {aviso.valor_recibido}</p>
          )}
          <ReviewActionRenderer item={aviso} readOnly={readOnly} busy={busy} onExecute={handleExecute} />
        </div>
      ))}
    </div>
  );
}
