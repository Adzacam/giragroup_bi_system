import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';

const value = dato => dato == null || dato === '' ? 'Sin dato' : dato;
const date = dato => dato ? new Date(dato).toLocaleString('es-BO') : 'Sin dato';

export default function PipelineTelemetryDrawer({ isOpen, onClose, docId }) {
  const [page, setPage] = useState(1);
  const [mapPage, setMapPage] = useState(1);
  const [tab, setTab] = useState('eventos');
  const [downloading, setDownloading] = useState(false);
  const downloadLock = useRef(false);
  const { data, error, isFetching, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'bitacora', docId, page, mapPage],
    queryFn: () => dataopsApi.getLogs(docId, page, mapPage),
    enabled: !!docId && isOpen,
    placeholderData: previous => previous,
  });
  useEffect(() => {
    if (!isOpen) return undefined;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const key = event => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', key);
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = overflow; };
  }, [isOpen, onClose]);
  useEffect(() => { if (error && isOpen) sileoToast.error({ title: 'No se pudo consultar la bitácora', description: mensajeError(error) }); }, [error, isOpen]);
  const download = async () => {
    if (downloadLock.current) return;
    downloadLock.current = true; setDownloading(true);
    try {
      const blob = await dataopsApi.downloadLogs(docId);
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `bitacora_documento_${docId}.md`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      sileoToast.success({ title: 'Bitácora descargada', description: 'El informe incluye todos los eventos y columnas registrados del documento.' });
    } catch (err) { sileoToast.error({ title: 'No se pudo descargar la bitácora', description: mensajeError(err) }); }
    finally { downloadLock.current = false; setDownloading(false); }
  };
  if (!isOpen) return null;
  const meta = data?.document_meta;
  const metrics = data?.summary_metrics;
  const pag = tab === 'eventos' ? data?.pagination : data?.matrix_pagination;
  return createPortal(<div className="modal-backdrop show" style={{ zIndex: 2000, justifyContent: 'flex-end' }}>
    <section role="dialog" aria-modal="true" aria-label="Bitácora del documento" style={{ width: 'min(980px,100vw)', height: '100%', overflowY: 'auto', background: 'var(--color-paper-white)', color: 'var(--color-ink-black)', padding: 24, boxShadow: 'var(--shadow-modal)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}><div><h2 className="serif-heading" style={{ fontSize: 24 }}>Bitácora del documento</h2><p style={{ marginTop: 8 }}>{meta?.nombre_archivo || 'Consultando archivo…'}</p></div><Button variant="ghost" onClick={onClose}>Cerrar bitácora</Button></div>
      <p style={{ margin: '16px 0', fontSize: 13, color: 'var(--color-slate-gray)' }}>Etapas y resultados registrados para este documento. Los mensajes internos y las muestras personales se omiten.</p>
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}><Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" onClick={async () => { const result = await refetch(); if (!result.error) sileoToast.success({ title: 'Bitácora actualizada' }); }}>Actualizar bitácora</Button><Button variant="ghost" isLoading={downloading} loadingText="Descargando…" disabled={!data || !!error} onClick={download}>Descargar informe</Button></div>
      {error ? <p role="alert">No se pudo consultar la bitácora. Puedes reintentarlo con Actualizar bitácora.</p> : !data ? <p role="status">Consultando eventos registrados…</p> : <>
        <div className="floating-artifact" style={{ padding: 20, display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
          <span>Filas de origen registradas: <strong>{value(metrics?.total_registros)}</strong></span><span>Eventos: <strong>{value(metrics?.eventos_registrados)}</strong></span><span>Columnas registradas: <strong>{value(metrics?.columnas_mapeadas)}</strong></span>
        </div>
        <details style={{ marginBottom: 24 }}><summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Detalles técnicos</summary><dl style={{ display: 'grid', gap: 10, paddingTop: 12 }}>
          {[['Documento', meta?.id_documento], ['Lote', meta?.id_lote], ['Institución', meta?.institucion], ['Periodo registrado', meta?.periodo], ['Fecha registrada', date(meta?.fecha_procesamiento)], ['Bloques guardados', metrics?.bloques_guardados], ['SHA-256', meta?.hash_sha256]].map(([label,dato]) => <div key={label}><dt style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{label}</dt><dd style={{ overflowWrap: 'anywhere' }}>{value(dato)}</dd></div>)}
        </dl></details>
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}><Button variant={tab === 'eventos' ? 'dark' : 'ghost'} onClick={() => setTab('eventos')}>Eventos</Button><Button variant={tab === 'columnas' ? 'dark' : 'ghost'} onClick={() => setTab('columnas')}>Columnas registradas</Button></div>
        <div aria-busy={isFetching} style={{ overflowX: 'auto' }}>{isFetching ? <p role="status">Consultando página…</p> : tab === 'eventos' ? <>
          <table className="dataops-table" style={{ width: '100%' }}><thead><tr><th>Fecha registrada</th><th>Etapa</th><th>Nivel</th><th>Duración registrada</th></tr></thead><tbody>{data.data.map(event => <tr key={event.id}><td>{date(event.fecha)}</td><td>{event.etapa}</td><td>{event.nivel}</td><td>{event.tiempo_ms == null ? 'Sin dato' : `${event.tiempo_ms} ms`}</td></tr>)}</tbody></table>{!data.data.length && <p style={{ padding: 20 }}>No hay eventos registrados para este documento.</p>}
        </> : <><table className="dataops-table" style={{ width: '100%' }}><thead><tr><th>Columna del archivo</th><th>Campo identificado</th><th>Regla registrada</th><th>Tipo</th></tr></thead><tbody>{data.normalization_matrix.map((row,index) => <tr key={index}><td>{value(row.original)}</td><td>{value(row.normalizado)}</td><td>{value(row.regla)}</td><td>{value(row.tipo)}</td></tr>)}</tbody></table>{!data.normalization_matrix.length && <p style={{ padding: 20 }}>No hay un mapeo de columnas registrado para este documento.</p>}</>}
        </div>
        <Paginacion pagina={tab === 'eventos' ? page : mapPage} totalPaginas={pag?.total_pages || 1} total={pag?.total_items || 0} filasPorPagina={5} disabled={isFetching} onChange={tab === 'eventos' ? setPage : setMapPage} />
      </>}
    </section>
  </div>, document.body);
}
