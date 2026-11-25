import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import BatchFlowLayout from './components/BatchFlowLayout';
import GruposBandeja from './components/GruposBandeja';
import ProgresoTarea from './components/ProgresoTarea';
import IntegridadLote from './components/IntegridadLote';
import CasoDetallePanel from './components/CasoDetallePanel';
import AvisosTab from './components/AvisosTab';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import useRevision from './hooks/useRevision';
import useRevisionAcciones from './hooks/useRevisionAcciones';
import { dataopsApi } from '../../api/dataopsApi';
import { confirmar, sileoToast } from '../../services/sileoToast';
import AnimatedNumberV2 from '../../v2/motion/AnimatedNumberV2';
import { mensajeError } from '../../utils/mensajeError';
import { textoMotivo } from '../../constants/motivosBandeja';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { toDataopsPath } from '../../v2/utils/v2Routes';

const INITIAL = { docId: null, vista: 'GRUPOS', search: '', area: 'TODAS', prioridad: 'TODAS', patron: 'TODOS', motivo: 'TODOS', page: 1, grupo: null };
const PRIORIDADES = [
  ['TODAS', 'Todas'],
  ['ALTA', 'Alta'],
  ['MEDIA', 'Media'],
  ['BAJA', 'Baja'],
];
const AREAS = {
  academica: 'Académica',
  evaluacion_docente: 'Evaluación docente',
  financiera: 'Financiera',
  comercial: 'Comercial',
  calidad: 'Calidad',
};
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';

export { CasoDetallePanel as CasoRevision };

function RevisionBandeja({ batchId }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { contexto, lectura, readOnly } = useLoteFlow();
  const vistaParam = searchParams.get('vista');
  const [filters, setFilters] = useDraftState('rev.filters.v4', INITIAL);
  useEffect(() => {
    if (vistaParam && ['GRUPOS', 'PENDIENTES', 'RESUELTOS', 'AVISOS'].includes(vistaParam) && filters.vista !== vistaParam) {
      setFilters(prev => ({ ...prev, vista: vistaParam, page: 1 }));
    }
  }, [vistaParam]);
  const [input, setInput] = useState(filters.search || '');
  const [exporting, setExporting] = useState(false);
  const [retryingPrep, setRetryingPrep] = useState(false);
  const [cancelingTask, setCancelingTask] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [justificacionBatch, setJustificacionBatch] = useState('');
  const [activeActionIdx, setActiveActionIdx] = useState(0);
  const exportLock = useRef(false);
  const actions = useRevisionAcciones();

  useEffect(() => {
    setSelectedIds([]);
  }, [batchId, filters.vista, filters.page, filters.docId, filters.area, filters.prioridad, filters.patron, filters.motivo, filters.grupo, filters.search]);
  const { data, error, isFetching, refetch } = useRevision(batchId, filters, !!contexto && filters.vista !== 'AVISOS');
  const { data: lecturaData } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'beto-reading-summary', String(batchId || ''), filters.docId || ''],
    queryFn: () => dataopsApi.getLoteBetoReading(batchId, { docId: filters.docId, page: 1, pageSize: 1 }),
    enabled: !lectura && !!batchId && !!contexto && typeof dataopsApi.getLoteBetoReading === 'function',
  });
  const summary = lectura || (lecturaData ? {
    status: lecturaData.status,
    autoCount: lecturaData.resumen_ejecutivo?.aceptados_automaticamente,
  } : undefined);
  const { data: task, refetch: refetchTask } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'consolidacion-task', String(batchId)],
    queryFn: () => dataopsApi.getBatchTask(batchId, 'CONSOLIDACION'),
    enabled: !!batchId,
    refetchInterval: q => q.state.data?.estado === 'EN_CURSO' ? 2000 : false,
  });
  const { data: prepTask, refetch: refetchPrepTask } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'preparacion-task', String(batchId)],
    queryFn: () => dataopsApi.getBatchTask(batchId, 'PREPARACION_REVISION'),
    enabled: !!batchId,
    refetchInterval: q => q.state.data?.estado === 'EN_CURSO' ? 2000 : false,
  });

  const preparing = prepTask?.estado === 'EN_CURSO';
  const processing = task?.estado === 'EN_CURSO' || preparing;
  const busy = actions.busy || processing;
  const previousTask = useRef(null);
  const previousPrepTask = useRef(null);

  useEffect(() => {
    if (previousTask.current === 'EN_CURSO' && task?.estado !== 'EN_CURSO') {
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    }
    previousTask.current = task?.estado;
  }, [task?.estado]);

  useEffect(() => {
    if (previousPrepTask.current === 'EN_CURSO' && prepTask?.estado !== 'EN_CURSO') {
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    }
    previousPrepTask.current = prepTask?.estado;
  }, [prepTask?.estado]);

  const items = data?.items || [];
  const selectedItem = items.find(it => String(it.id) === String(selectedId)) || items[0] || null;

  useEffect(() => {
    if (items.length && (!selectedId || !items.some(it => String(it.id) === String(selectedId)))) {
      setSelectedId(items[0].id);
      setActiveActionIdx(0);
    }
  }, [items, selectedId]);

  // Atajos de teclado A / D / ↑ / ↓ (DF-L3 e)
  useEffect(() => {
    if (!['PENDIENTES', 'RESUELTOS'].includes(filters.vista) || !items.length) return;
    const onKeyDown = (e) => {
      const tag = (e.target?.tagName || '').toUpperCase();
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || e.target?.isContentEditable) return;
      const curIdx = Math.max(0, items.findIndex(it => String(it.id) === String(selectedItem?.id)));
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = items[Math.min(items.length - 1, curIdx + 1)];
        if (next) { setSelectedId(next.id); setActiveActionIdx(0); }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = items[Math.max(0, curIdx - 1)];
        if (prev) { setSelectedId(prev.id); setActiveActionIdx(0); }
      } else if ((e.key === 'a' || e.key === 'A') && selectedItem && !readOnly && filters.vista === 'PENDIENTES') {
        setActiveActionIdx(0);
      } else if ((e.key === 'd' || e.key === 'D') && selectedItem && !readOnly && filters.vista === 'PENDIENTES') {
        const dIdx = (selectedItem.acciones || []).findIndex(a => String(a.codigo || '').includes('DESCARTAR'));
        if (dIdx >= 0) setActiveActionIdx(dIdx);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [filters.vista, items, selectedItem, readOnly]);

  const triggerPrepManual = async () => {
    if (retryingPrep) return;
    setRetryingPrep(true);
    try {
      const res = await dataopsApi.prepararRevision({ id_lote: Number(batchId) });
      if (res?.status === 'already_prepared') queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      else avisarTareaIniciada();
      await refetchPrepTask();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo preparar la revisión', description: mensajeError(err) });
    } finally {
      setRetryingPrep(false);
    }
  };

  const setFilter = (key, value) => setFilters(prev => ({
    ...prev, [key]: value, page: 1,
    ...(key === 'vista' || key === 'docId' ? { grupo: null } : {}),
  }));

  useEffect(() => {
    const timer = setTimeout(() => {
      if (input.trim() !== filters.search) setFilters(prev => ({ ...prev, search: input.trim(), page: 1 }));
    }, 300);
    return () => clearTimeout(timer);
  }, [input, filters.search, setFilters]);

  useEffect(() => { if (error) sileoToast.error({ title: 'No se pudo consultar la revisión', description: mensajeError(error) }); }, [error]);
  useEffect(() => {
    if (data?.pagination && filters.page > data.pagination.total_pages) setFilters(prev => ({ ...prev, page: data.pagination.total_pages }));
  }, [data, filters.page, setFilters]);

  const refresh = async () => {
    const result = await refetch();
    if (!result.error) sileoToast.success({ title: 'Bandeja actualizada', description: 'Se consultaron los casos guardados.' });
  };

  const exportCsv = async () => {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true);
    try {
      const blob = await dataopsApi.exportIncidencias(batchId, filters);
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `incidencias_lote_${batchId}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      sileoToast.success({ title: 'Exportación descargada', description: 'Incluye los casos seleccionados y las cédulas protegidas.' });
    } catch (err) { sileoToast.error({ title: 'No se pudo exportar', description: mensajeError(err) }); }
    finally { exportLock.current = false; setExporting(false); }
  };

  const consolidate = () => actions.schedule('Consolidar el lote completo', async () => {
    const result = await dataopsApi.iniciarConsolidacion({ id_lote: Number(batchId) });
    avisarTareaIniciada();
    sileoToast.info({ title: 'Consolidación en curso', description: 'Puedes seguir el avance y su resultado desde las notificaciones.' });
    return result;
  });

  const activeTask = preparing ? prepTask : task;
  const cancelActiveTask = async () => {
    const tid = activeTask?.id;
    if (!tid || cancelingTask) return;
    const label = preparing ? 'preparación de casos' : 'consolidación';
    if (!await confirmar({ title: `Cancelar ${label}`, description: 'Se detendrá la tarea en curso para este lote.', confirmText: 'Cancelar tarea' })) return;
    setCancelingTask(true);
    try {
      await dataopsApi.cancelarTarea(tid);
      sileoToast.info({ title: 'Tarea cancelada', description: 'El proceso se detuvo. Puedes reintentar o reiniciar el lote.' });
      await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      await Promise.all([refetchTask(), refetchPrepTask()]);
    } catch (err) {
      sileoToast.error({ title: 'No se pudo cancelar la tarea', description: mensajeError(err) });
    } finally { setCancelingTask(false); }
  };

  const total = filters.vista === 'GRUPOS' ? data?.total_casos : data?.total;
  const showMasterDetail = ['PENDIENTES', 'RESUELTOS'].includes(filters.vista);

  if (!batchId) {
    return (
      <BatchFlowLayout currentStep={3}>
        <div className="floating-artifact" style={{ padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <p style={{ margin: 0 }}>Selecciona un lote desde el historial de carga.</p>
          <a href="/dataops/ingesta" className="btn-secondary">Ir al historial de carga</a>
        </div>
      </BatchFlowLayout>
    );
  }

  return (
    <BatchFlowLayout currentStep={3} showReadOnlyContent selectionDisabled={actions.busy} selectedDocId={filters.docId} onSelectDocId={value => { if (!actions.busy) setFilter('docId', value); }}>
      <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
        <h2 className="serif-heading" style={{ fontSize: 22 }}>Revisión y consolidación</h2>
        <p style={{ fontSize: 13, color: 'var(--color-slate-gray)', margin: '10px 0' }}>Cada caso ofrece acciones propias según su motivo. Usa ↑/↓ para recorrer casos, A para la acción principal y D para descartar.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, margin: '16px 0' }}>
          <span>Filas de texto: <strong><AnimatedNumberV2 value={fmt(contexto?.total_registros)} animateOnceKey={`rev-${batchId}-filas`} /></strong></span>
          <span>Casos en la selección: <strong>{isFetching ? 'Consultando…' : <AnimatedNumberV2 value={fmt(total)} animateOnceKey={`rev-${batchId}-casos`} />}</strong></span>
          <span>Aceptación directa en la lectura: <strong><AnimatedNumberV2 value={fmt(summary?.autoCount)} animateOnceKey={`rev-${batchId}-auto`} /></strong></span>
        </div>
        {!readOnly && <Button disabled={busy || summary?.status !== 'success'} isLoading={actions.sending || processing} loadingText="Procesando…" onClick={consolidate}>Consolidar lote</Button>}
        {!readOnly && summary?.status !== 'success' && <p style={{ marginTop: 10 }}>Primero consulta o inicia la lectura de BETO en el paso ②.</p>}
        {readOnly && <p>El lote está cerrado. Las consultas y exportaciones siguen disponibles.</p>}
      </div>
      <IntegridadLote key={batchId} batchId={batchId} />
      {actions.pending.map(op => <div key={op.id} className="dataops-banner-info" role="status" style={{ marginBottom: 12 }}><span>{op.title}: se enviará en {op.seconds} s.</span><Button variant="ghost" onClick={() => actions.cancel(op.id)}>Deshacer</Button></div>)}
      {processing && <ProgresoTarea titulo={preparing ? 'Preparando casos de revisión' : 'Consolidando el lote'} tarea={preparing ? prepTask : task} nota={preparing ? 'Preparando casos… se habilita al terminar.' : 'El proceso continúa en segundo plano.'} onCancel={activeTask?.id ? cancelActiveTask : undefined} canceling={cancelingTask} cancelLabel="Cancelar tarea" />}
      {!readOnly && summary?.status === 'success' && !processing && (prepTask === null || prepTask?.estado === 'FALLIDA') && (
        <div className="dataops-banner-info" role={prepTask?.estado === 'FALLIDA' ? 'alert' : 'status'} style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span>{prepTask?.estado === 'FALLIDA' ? `La preparación de casos falló${prepTask?.mensaje_error ? `: ${prepTask.mensaje_error}` : '.'}` : 'Este lote aún no tiene la bandeja preparada.'}</span>
          <Button variant="ghost" isLoading={retryingPrep} loadingText="Preparando…" disabled={retryingPrep} onClick={triggerPrepManual}>{prepTask?.estado === 'FALLIDA' ? 'Reintentar preparación' : 'Preparar revisión'}</Button>
        </div>
      )}
      <div className="floating-artifact" style={{ padding: 20, marginBottom: 20 }}>
        <div role="tablist" aria-label="Vistas de bandeja" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
          {[['GRUPOS', 'Por grupos'], ['PENDIENTES', 'Casos pendientes'], ['RESUELTOS', 'Casos resueltos'], ['AVISOS', 'Avisos']].map(([value, label]) => (
            <Button variant="ghost" role="tab" aria-selected={filters.vista === value} key={value} style={{ borderColor: filters.vista === value ? 'var(--color-gira-gold)' : 'var(--color-border)', background: filters.vista === value ? 'var(--dataops-info-bg)' : undefined, color: filters.vista === value ? 'var(--dataops-info-text)' : undefined }} disabled={actions.busy} onClick={() => setFilter('vista', value)}>{label}</Button>
          ))}
        </div>
        {filters.vista !== 'AVISOS' && (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
            <label style={{ flex: '1 1 240px', fontSize: 12 }}>Buscar en la selección<input className="dataops-input" aria-label="Buscar casos" value={input} onChange={e => setInput(e.target.value)} maxLength={200} disabled={actions.busy} placeholder="Nombre, módulo, archivo o motivo" /></label>
            {filters.vista !== 'GRUPOS' && <label style={{ fontSize: 12 }}>Área<select aria-label="Área de revisión" className="dataops-select" value={filters.area} disabled={actions.busy} onChange={e => setFilter('area', e.target.value)}><option value="TODAS">Todas</option>{Object.entries(AREAS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
            {filters.vista !== 'GRUPOS' && <label style={{ fontSize: 12 }}>Prioridad<select aria-label="Prioridad de revisión" className="dataops-select" value={filters.prioridad || 'TODAS'} disabled={actions.busy} onChange={e => setFilter('prioridad', e.target.value)}>{PRIORIDADES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
            <Button variant="ghost" disabled={actions.busy} onClick={() => { setFilters(INITIAL); setInput(''); }}>Limpiar filtros</Button>
            <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={actions.busy} onClick={refresh}>Actualizar</Button>
            <Button variant="ghost" isLoading={exporting} loadingText="Exportando…" disabled={!data || actions.busy || isFetching || filters.vista === 'GRUPOS'} onClick={exportCsv}>Exportar incidencias</Button>
          </div>
        )}
        {(filters.grupo || (filters.patron && filters.patron !== 'TODOS') || (filters.motivo && filters.motivo !== 'TODOS')) && (
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', fontSize: 12 }}>
            {filters.grupo && <Button variant="ghost" disabled={actions.busy} onClick={() => setFilter('grupo', null)}>Quitar filtro de grupo</Button>}
            {filters.patron && filters.patron !== 'TODOS' && <Button variant="ghost" disabled={actions.busy} onClick={() => setFilter('patron', 'TODOS')}>Banda: {filters.patron} ✕</Button>}
            {filters.motivo && filters.motivo !== 'TODOS' && <Button variant="ghost" disabled={actions.busy} onClick={() => setFilter('motivo', 'TODOS')}>Regla: {textoMotivo(filters.motivo)} ✕</Button>}
          </div>
        )}
      </div>
      <div aria-busy={isFetching} className="floating-artifact" style={{ padding: 20 }}>
        {filters.vista === 'AVISOS' ? (
          <AvisosTab batchId={batchId} docId={filters.docId} readOnly={readOnly} />
        ) : error ? <p role="alert">No se pudo consultar la bandeja. Pulsa Actualizar para reintentarlo.</p>
          : isFetching && !data ? <p role="status">Consultando casos…</p>
          : filters.vista === 'GRUPOS' ? (
            <GruposBandeja
              data={data}
              readOnly={readOnly}
              busy={busy}
              onSelectPatron={patron => { setInput(''); setFilters(prev => ({ ...prev, vista: 'PENDIENTES', patron, motivo: 'TODOS', grupo: null, page: 1 })); }}
              onSelectMotivo={motivo => { setInput(''); setFilters(prev => ({ ...prev, vista: 'PENDIENTES', motivo, patron: 'TODOS', grupo: null, page: 1 })); }}
              onVerIndividual={clave => { setInput(''); setFilters(prev => ({ ...prev, vista: 'PENDIENTES', grupo: clave, page: 1, search: '', area: 'TODAS', patron: 'TODOS', motivo: 'TODOS' })); }}
              onResolver={(group, extra = {}) => actions.schedule(`Resolver grupo de ${group.n} casos`, () => dataopsApi.aprobarGrupo({ clave: group.clave, accion: group.accion_grupo, docIds: data.doc_ids, ...extra }))}
            />
          ) : !items.length ? <p role="status">No hay casos para esta selección.</p>
          : showMasterDetail && (
            <>
              {!readOnly && filters.vista === 'PENDIENTES' && (() => {
                const esBandaCritica = filters.patron === 'muy_distinto';
                const esBloqueado = it => it.motivo === 'CI_NOMBRE_DISCORDANTE' && (it.patron_codigo === 'muy_distinto' || (it.similitud != null && Number(it.similitud) < 30));
                const seleccionables = items.filter(it => !esBloqueado(it)).map(it => String(it.id));
                const todosMarcados = seleccionables.length > 0 && seleccionables.every(id => selectedIds.includes(id));
                if (esBandaCritica) {
                  return (
                    <div role="note" style={{ marginBottom: 12, padding: '10px 12px', borderRadius: 10, background: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)', fontSize: 12 }}>
                      Similitud &lt; 30 %: revisión individual obligatoria (no se permiten acciones en bloque).
                    </div>
                  );
                }
                const runBatch = (accion) => {
                  if (!selectedIds.length) return;
                  const etiqueta = accion === 'DESCARTAR' ? 'Descartar' : 'Confirmar';
                  actions.schedule(`${etiqueta} ${selectedIds.length} casos seleccionados`, () =>
                    dataopsApi.batchResolveReviewItems({
                      item_ids: selectedIds,
                      accion,
                      justificacion: justificacionBatch.trim() || undefined,
                    })
                  );
                };
                return (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 12, padding: '10px 12px', borderRadius: 10, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
                    <Button variant="ghost" disabled={busy || !seleccionables.length} onClick={() => setSelectedIds(todosMarcados ? [] : seleccionables)}>
                      {todosMarcados ? 'Deseleccionar página' : `Seleccionar página (${seleccionables.length})`}
                    </Button>
                    <input
                      type="text"
                      className="dataops-input"
                      aria-label="Justificación de acción en lote"
                      placeholder="Justificación (opcional)"
                      value={justificacionBatch}
                      onChange={e => setJustificacionBatch(e.target.value)}
                      maxLength={200}
                      style={{ flex: '1 1 180px', minWidth: 160 }}
                    />
                    <Button variant="primary" disabled={busy || !selectedIds.length} isLoading={actions.sending} onClick={() => runBatch('APROBAR')}>
                      Confirmar seleccionados ({selectedIds.length})
                    </Button>
                    <Button variant="ghost" disabled={busy || !selectedIds.length} isLoading={actions.sending} onClick={() => runBatch('DESCARTAR')}>
                      Descartar seleccionados ({selectedIds.length})
                    </Button>
                  </div>
                );
              })()}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, alignItems: 'start' }}>
              <div role="listbox" aria-label="Lista de casos" style={{ display: 'grid', gap: 8, maxHeight: 560, overflowY: 'auto' }}>
                {items.map(it => {
                  const active = String(it.id) === String(selectedItem?.id);
                  const bloqueado = it.motivo === 'CI_NOMBRE_DISCORDANTE' && (it.patron_codigo === 'muy_distinto' || (it.similitud != null && Number(it.similitud) < 30));
                  const checked = selectedIds.includes(String(it.id));
                  return (
                    <div key={it.id} style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
                      {!readOnly && filters.vista === 'PENDIENTES' && (
                        <label style={{ display: 'flex', alignItems: 'center', paddingLeft: 4 }} title={bloqueado ? 'Similitud < 30 %: requiere revisión individual' : 'Seleccionar caso'}>
                          <input
                            type="checkbox"
                            aria-label={`Seleccionar caso ${it.id}`}
                            disabled={busy || bloqueado}
                            checked={checked}
                            onChange={e => {
                              const sid = String(it.id);
                              setSelectedIds(prev => e.target.checked ? [...prev, sid] : prev.filter(x => x !== sid));
                            }}
                          />
                        </label>
                      )}
                      <button type="button" role="option" aria-selected={active} onClick={() => { setSelectedId(it.id); setActiveActionIdx(0); }} style={{ flex: 1, textAlign: 'left', padding: '10px 12px', borderRadius: 10, cursor: 'pointer', border: `1px solid ${active ? 'var(--color-gira-gold)' : 'var(--color-border)'}`, background: active ? 'var(--dataops-info-bg)' : 'var(--color-pure-white)', color: 'var(--color-ink-black)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 12, fontWeight: 700 }}>
                          <span>{textoMotivo(it.motivo, it.motivo_label)}</span>
                          <span style={{ display: 'flex', gap: 6, alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-slate-gray)' }}>
                            {it.prioridad && (
                              <span style={{ fontFamily: 'inherit', fontSize: 10, padding: '1px 6px', borderRadius: 999, background: it.prioridad === 'ALTA' ? 'var(--dataops-warning-bg)' : 'var(--dataops-info-bg)', color: it.prioridad === 'ALTA' ? 'var(--dataops-warning-text)' : 'var(--dataops-info-text)' }}>
                                {it.prioridad}
                              </span>
                            )}
                            #{it.id}
                          </span>
                        </div>
                        <p style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 4 }}>{it.archivo_origen || 'Sin archivo'} · {it.ci_enmascarado || 'Sin CI'}</p>
                      </button>
                    </div>
                  );
                })}
              </div>
              <CasoDetallePanel item={selectedItem} readOnly={readOnly} isResuelto={filters.vista === 'RESUELTOS'} busy={busy} schedule={actions.schedule} activeActionIdx={activeActionIdx} onSelectActionIdx={setActiveActionIdx} />
            </div>
            </>
          )}
        {filters.vista !== 'AVISOS' && <Paginacion pagina={filters.page} totalPaginas={data?.pagination?.total_pages || 1} total={data?.pagination?.total_items || 0} filasPorPagina={filters.vista === 'GRUPOS' ? 5 : 20} disabled={isFetching || actions.busy} onChange={page => setFilters(prev => ({ ...prev, page }))} />}
      </div>
      <Button variant="ghost" style={{ marginTop: 20 }} disabled={actions.busy} onClick={() => navigate(toDataopsPath(`/lote/${batchId}/beto`, location.pathname))}>Volver a lectura de BETO</Button>
    </BatchFlowLayout>
  );
}

export default function HumanReviewFlowView() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return <RevisionBandeja key={batchId || 'sin-lote'} batchId={batchId} />;
}
