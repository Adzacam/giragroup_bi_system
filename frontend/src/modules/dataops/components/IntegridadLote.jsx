import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';

const fmt = value => value == null ? 'Sin dato' : value.toLocaleString('es-BO');
const TIPOS = { academicos: 'académicos', financieros: 'financieros', respuestas: 'respuestas', rentabilidad: 'de rentabilidad', costos: 'de costos', convenios: 'convenios' };

export default function IntegridadLote({ batchId }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const { data, isFetching, isError, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'integridad', batchId, page],
    queryFn: () => dataopsApi.getIntegridad(batchId, page),
    enabled: open && !!batchId,
  });
  return <details className="floating-artifact" style={{ padding: 20, marginBottom: 20 }} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary style={{ cursor: 'pointer' }}>Comprobar conteos del lote</summary>
    {open && <div style={{ marginTop: 16 }} aria-busy={isFetching}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Origen: conteo registrado en la ingesta. Texto: líneas guardadas para procesar. Lectura: filas evaluadas por BETO. Directas: aceptadas en la lectura; su carga se comprueba en los hechos.</p>
      <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" onClick={() => refetch()}>Actualizar conteos</Button>
      {isError ? <p role="alert">No se pudieron consultar los conteos. Pulsa Actualizar conteos para reintentar.</p> : isFetching ? <p role="status">Consultando conteos…</p> : data && <>
        <div style={{ overflowX: 'auto', marginTop: 12 }}><table className="dataops-table" style={{ width: '100%' }}>
          <thead><tr><th>Documento</th><th>Filas de origen / texto</th><th>Filas de lectura</th><th>Directas en lectura</th><th>Casos pendientes / resueltos</th><th>Hechos guardados</th></tr></thead>
          <tbody>{data.data.map(row => <tr key={row.id_documento}>
            <td>#{row.id_documento}</td><td>{fmt(row.filas_origen)} / {fmt(row.filas_texto)}</td><td>{fmt(row.filas_lectura)}</td><td>{fmt(row.filas_directas)}</td>
            <td>{fmt(row.casos_pendientes)} / {fmt(row.casos_resueltos)}</td>
            <td>{Object.entries(row.hechos).filter(([, n]) => n > 0).map(([tipo, n]) => `${fmt(n)} ${TIPOS[tipo]}`).join(' · ') || 'Sin hechos vinculados'}</td>
          </tr>)}</tbody>
        </table></div>
        <Paginacion pagina={page} totalPaginas={data.pagination.total_pages} total={data.pagination.total_items} filasPorPagina={5} onChange={setPage} disabled={isFetching} />
        <p style={{ fontSize: 12, marginTop: 12 }}>{data.nota}</p>
      </>}
    </div>}
  </details>;
}
