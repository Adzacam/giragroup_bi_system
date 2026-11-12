import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import BatchFlowLayout from './components/BatchFlowLayout';
import GruposBandeja from './components/GruposBandeja';
import ProgresoTarea from './components/ProgresoTarea';
import IntegridadLote from './components/IntegridadLote';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import { useRevealCi } from './hooks/useRevealCi';
import useRevision from './hooks/useRevision';
import useRevisionAcciones from './hooks/useRevisionAcciones';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import { textoMotivo } from '../../constants/motivosBandeja';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';

const INITIAL = { docId: null, vista: 'GRUPOS', search: '', area: 'TODAS', page: 1, grupo: null };
const AREAS = { academica: 'Académica', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad', evaluacion_docente: 'Evaluación docente' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';

function CasoRevision({ item, readOnly, busy, schedule }) {
  const [revealed, toggleCi] = useRevealCi();
  const [revealing, setRevealing] = useState(false);
  const revealLock = useRef(false);
  const [form, setForm] = useState(() => ({ estudiante_resuelto: item.estudiante || '', ci_corregida: '', modulo_resuelto: item.modulo_detectado || '', nota_final: item.nota_final ?? '', monto_deuda: item.monto_deuda ?? '', cuotas_impagas: item.cuotas_impagas ?? '', mes: item.mes ?? '', gestion: item.gestion ?? '', nota_auditor: '', motivo_descarte: '', docente_resuelto: '' }));
  const [discard, setDiscard] = useState(false);
  const field = (key, label, type = 'text', limits = {}) => <label style={{ fontSize: 12 }}>{label}<input aria-label={`${label} del caso ${item.id}`} className="dataops-input" type={type} value={form[key]} onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))} disabled={busy || readOnly} maxLength={type === 'text' ? 200 : undefined} {...limits} /></label>;
  const approve = () => {
    const payload = { accion: 'APROBAR' };
    for (const [key, value] of Object.entries(form)) {
      if (value !== '' && key !== 'motivo_descarte') payload[key] = ['nota_final','monto_deuda','cuotas_impagas','mes','gestion'].includes(key) ? Number(value) : value.trim();
    }
    schedule(`Aprobar caso ${item.id}`, () => dataopsApi.resolveReviewItem(item.id, payload));
  };
  const reveal = async () => {
    if (revealLock.current) return;
    revealLock.current = true;
    setRevealing(true);
    try { await toggleCi(item.id); } finally { revealLock.current = false; setRevealing(false); }
  };
  const hasCi = item.ci_enmascarado && item.ci_enmascarado !== 'No provisto';
  return <details className="floating-artifact" style={{ padding: 18, marginBottom: 12 }}>
    <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}><strong>Caso {item.id}</strong> · {textoMotivo(item.motivo)} · {item.estudiante || 'Sin nombre identificado'}</summary>
    <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '12px 0' }}>{item.archivo_origen || 'Sin archivo'} · {AREAS[item.area] || 'Sin área'} · Índice: {item.indice_registro == null ? 'Sin dato' : `${item.indice_registro} %`}</p>
    <p>{item.por_que_detuvo}</p>
    <p style={{ margin: '12px 0' }}>Cédula: {revealed[item.id] || item.ci_enmascarado || 'Sin dato'} {hasCi && <Button variant="ghost" isLoading={revealing} loadingText="Consultando…" onClick={reveal}>{revealed[item.id] ? 'Ocultar cédula' : 'Revelar con auditoría'}</Button>}</p>
    <details style={{ marginBottom: 12 }}><summary style={{ cursor: 'pointer' }}>Ver texto original protegido</summary><p style={{ fontSize: 12, overflowWrap: 'anywhere', padding: '12px 0' }}>{item.que_vio || 'Sin texto disponible'}</p></details>
    {item.sugerencia && <p style={{ marginBottom: 12 }}>Sugerencia guardada: {item.sugerencia}</p>}
    {readOnly ? <p>Estado: {item.estado_resolucion === 'DESCARTADO' ? 'Descartado' : item.estado_resolucion === 'RESUELTO_HUMANO' ? 'Resuelto' : 'Pendiente de revisión'}</p> : <>
      {item.manual_presupuesto && <p className="dataops-banner-info">Esta fila requiere revisar su clasificación. La aprobación como persona está bloqueada.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12, margin: '16px 0' }}>
        {item.area !== 'evaluacion_docente' && field('estudiante_resuelto', 'Nombre del estudiante')}
        {item.tipo_entidad !== 'HECHO' && field('ci_corregida', 'Cédula corregida (opcional)')}
        {item.area !== 'evaluacion_docente' ? field('modulo_resuelto', 'Módulo') : <p>Módulo: {item.modulo_detectado || 'Sin dato'}</p>}
        {item.area === 'academica' && field('nota_final', 'Nota sobre 100', 'number', { min: 0, max: 100, step: 'any' })}
        {item.area === 'financiera' && <>{field('monto_deuda', 'Monto de deuda', 'number', { min: 0, step: 'any' })}{field('cuotas_impagas', 'Cuotas impagas', 'number', { min: 0 })}</>}
        {item.area === 'evaluacion_docente' && field('docente_resuelto', 'Docente')}
        {field('mes', 'Mes', 'number', { min: 1, max: 12 })}{field('gestion', 'Gestión', 'number', { min: 2000, max: 2100 })}
        {field('nota_auditor', 'Justificación de la corrección')}
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}><Button disabled={busy || item.locked || item.manual_presupuesto} onClick={approve}>Programar aprobación</Button><Button variant="ghost" disabled={busy || item.locked} onClick={() => setDiscard(value => !value)}>Descartar caso</Button></div>
      {item.locked && <p>Otro auditor está revisando este caso.</p>}
      {discard && <div style={{ marginTop: 16 }}>{field('motivo_descarte', 'Motivo del descarte')}<p style={{ fontSize: 12, margin: '8px 0' }}>El caso quedará registrado como descartado. Revisa el motivo antes de continuar.</p><Button variant="ghost" disabled={busy || !form.motivo_descarte.trim()} onClick={() => schedule(`Descartar caso ${item.id}`, () => dataopsApi.resolveReviewItem(item.id, { accion: 'DESCARTAR', motivo_descarte: form.motivo_descarte.trim() }))}>Programar descarte</Button></div>}
    </>}
  </details>;
}

function Revision({ batchId }) {
  const navigate = useNavigate();
  const { contexto, readOnly } = useLoteFlow();
  const [filters, setFilters] = useDraftState('review.filters.v4', INITIAL);
  const [input, setInput] = useState(filters.search);
  const [exporting, setExporting] = useState(false);
  const exportLock = useRef(false);
  const actions = useRevisionAcciones();
  const { data, error, isFetching, refetch } = useRevision(batchId, filters, !!contexto);
  const { data: summary } = useQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'review-summary', batchId], queryFn: () => dataopsApi.getLoteResumen(batchId), enabled: !!batchId && !!contexto });
  const { data: task } = useQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'review-task', batchId], queryFn: () => dataopsApi.getTareaLote(batchId), enabled: !!batchId && !!contexto, refetchInterval: query => query.state.data?.estado === 'EN_CURSO' ? 2000 : false });
  const processing = task?.estado === 'EN_CURSO';
  const busy = actions.busy || processing;
  const previousTask = useRef(null);
  useEffect(() => {
    if (previousTask.current === 'EN_CURSO' && task?.estado !== 'EN_CURSO') queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    previousTask.current = task?.estado;
  }, [task?.estado]);
  const setFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value, page: 1, ...(key === 'vista' || key === 'docId' ? { grupo: null } : {}) }));
  useEffect(() => {
    const timer = setTimeout(() => { if (input.trim() !== filters.search) setFilters(prev => ({ ...prev, search: input.trim(), page: 1 })); }, 300);
    return () => clearTimeout(timer);
  }, [input, filters.search, setFilters]);
  useEffect(() => { if (error) sileoToast.error({ title: 'No se pudo consultar la revisión', description: mensajeError(error) }); }, [error]);
  useEffect(() => {
    if (data?.pagination && filters.page > data.pagination.total_pages) setFilters(prev => ({ ...prev, page: data.pagination.total_pages }));
  }, [data, filters.page, setFilters]);
  const refresh = async () => { const result = await refetch(); if (!result.error) sileoToast.success({ title: 'Bandeja actualizada', description: 'Se consultaron los casos guardados.' }); };
  const exportCsv = async () => {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true);
    try {
      const blob = await dataopsApi.exportIncidencias(batchId, filters);
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `incidencias_lote_${batchId}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      sileoToast.success({ title: 'Exportación descargada', description: 'Incluye todos los casos de la selección y las cédulas protegidas.' });
    } catch (err) { sileoToast.error({ title: 'No se pudo exportar', description: mensajeError(err) }); }
    finally { exportLock.current = false; setExporting(false); }
  };
  const consolidate = () => actions.schedule('Consolidar el lote completo', async () => {
    const result = await dataopsApi.iniciarConsolidacion({ id_lote: Number(batchId) });
    avisarTareaIniciada();
    sileoToast.info({ title: 'Consolidación en curso', description: 'Puedes seguir el avance y su resultado desde las notificaciones.' });
    return result;
  });
  const total = filters.vista === 'GRUPOS' ? data?.total_casos : data?.total;
  return <BatchFlowLayout currentStep={4} showReadOnlyContent selectionDisabled={actions.busy} selectedDocId={filters.docId} onSelectDocId={value => { if (!actions.busy) setFilter('docId', value); }}>
    <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
      <h2 className="serif-heading" style={{ fontSize: 22 }}>Revisión y consolidación</h2>
      <p style={{ fontSize: 13, color: 'var(--color-slate-gray)', margin: '10px 0' }}>Comprueba los casos pendientes. Aprobar un caso guarda su corrección e incorpora el registro; consolidar procesa las filas del lote completo.</p>
      <p style={{ fontSize: 12 }}>85 % o más: directo cuando cumple las reglas · Desde 60 % y menos de 85 %: marcado para revisión · Menos de 60 %: bandeja.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, margin: '16px 0' }}><span>Filas de texto: <strong>{fmt(contexto?.total_registros)}</strong></span><span>Casos en la selección: <strong>{isFetching ? 'Consultando…' : fmt(total)}</strong></span><span>Aceptación directa en la lectura: <strong>{fmt(summary?.autoCount)}</strong></span></div>
      {!readOnly && <Button disabled={busy || summary?.status !== 'success'} isLoading={actions.sending || processing} loadingText="Procesando…" onClick={consolidate}>Consolidar lote</Button>}
      {!readOnly && summary?.status !== 'success' && <p style={{ marginTop: 10 }}>Primero consulta o inicia la lectura de BETO en el paso ③.</p>}
      {readOnly && <p>El lote está cerrado. Las consultas y exportaciones siguen disponibles.</p>}
    </div>
    <IntegridadLote key={batchId} batchId={batchId} />
    {actions.pending && <div className="dataops-banner-info" role="status" style={{ marginBottom: 20 }}><span>{actions.pending.title}: se enviará en {actions.pending.seconds} s. Salir de esta pantalla cancela la espera.</span><Button variant="ghost" onClick={actions.cancel}>Deshacer</Button></div>}
    {processing && <ProgresoTarea titulo="Consolidando el lote" tarea={task} nota="El proceso continúa en segundo plano y avisará al terminar." />}
    <div className="floating-artifact" style={{ padding: 20, marginBottom: 20 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>{[['GRUPOS','Por grupos'],['PENDIENTES','Casos pendientes'],['RESUELTOS','Casos resueltos']].map(([value,label]) => <Button variant="ghost" key={value} style={{ borderColor: filters.vista === value ? 'var(--color-gira-gold)' : 'var(--color-border)', background: filters.vista === value ? 'var(--dataops-info-bg)' : undefined, color: filters.vista === value ? 'var(--dataops-info-text)' : undefined }} disabled={actions.busy} aria-pressed={filters.vista === value} onClick={() => setFilter('vista',value)}>{label}</Button>)}</div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
        <label style={{ flex: '1 1 240px', fontSize: 12 }}>Buscar en la selección<input className="dataops-input" aria-label="Buscar casos" value={input} onChange={e => setInput(e.target.value)} maxLength={200} disabled={actions.busy} placeholder="Nombre, módulo, archivo o motivo" /></label>
        {filters.vista !== 'GRUPOS' && <label style={{ fontSize: 12 }}>Área<select aria-label="Área de revisión" className="dataops-select" value={filters.area} disabled={actions.busy} onChange={e => setFilter('area',e.target.value)}><option value="TODAS">Todas</option>{Object.entries(AREAS).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
        <Button variant="ghost" disabled={actions.busy} onClick={() => { setFilters(INITIAL); setInput(''); }}>Limpiar filtros</Button>
        <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={actions.busy} onClick={refresh}>Actualizar</Button>
        <Button variant="ghost" isLoading={exporting} loadingText="Exportando…" disabled={!data || actions.busy || isFetching || filters.vista === 'GRUPOS'} onClick={exportCsv}>Exportar incidencias</Button>
      </div>
      {filters.grupo && <p style={{ marginTop: 12 }}>Mostrando los casos del grupo seleccionado. <Button variant="ghost" disabled={actions.busy} onClick={() => setFilter('grupo',null)}>Ver todos los casos</Button></p>}
      {!readOnly && filters.vista === 'PENDIENTES' && !filters.grupo && !filters.search && filters.area === 'TODAS' && <Button variant="ghost" style={{ marginTop: 14 }} disabled={busy || isFetching || !data?.un_clic_total} onClick={() => actions.schedule(`Aprobar ${data.un_clic_total} casos con datos completos o coincidencia de nombre`, () => dataopsApi.aprobarCasosUnClic(batchId, filters.docId))}>Aprobar casos verificados ({fmt(data?.un_clic_total)})</Button>}
    </div>
    <div aria-busy={isFetching} className="floating-artifact" style={{ padding: 20 }}>
      {error ? <p role="alert">No se pudo consultar la bandeja. Pulsa Actualizar para reintentarlo.</p> : isFetching || !data ? <p role="status">Consultando casos…</p> : filters.vista === 'GRUPOS' ? <GruposBandeja data={data} readOnly={readOnly} busy={busy} onVerIndividual={clave => { setInput(''); setFilters(prev => ({ ...prev, vista: 'PENDIENTES', grupo: clave, page: 1, search: '', area: 'TODAS' })); }} onResolver={(group, extra = {}) => actions.schedule(`Resolver grupo de ${group.n} casos`, () => dataopsApi.aprobarGrupo({ clave: group.clave, accion: group.accion_grupo, docIds: data.doc_ids, ...extra }))} /> : !data.items?.length ? <p role="status">No hay casos para esta selección.</p> : data.items.map(item => <CasoRevision key={`${item.id}-${filters.vista}`} item={item} readOnly={readOnly || filters.vista === 'RESUELTOS'} busy={busy} schedule={actions.schedule} />)}
      <Paginacion pagina={filters.page} totalPaginas={data?.pagination?.total_pages || 1} total={data?.pagination?.total_items || 0} filasPorPagina={5} disabled={isFetching || actions.busy} onChange={page => setFilters(prev => ({ ...prev, page }))} />
    </div>
    <Button variant="ghost" style={{ marginTop: 20 }} disabled={actions.busy} onClick={() => navigate(`/dataops/lote/${batchId}/beto`)}>Volver a lectura de BETO</Button>
  </BatchFlowLayout>;
}

export default function HumanReviewFlowView() {
  const { id } = useParams(); const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return batchId ? <Revision key={batchId} batchId={batchId} /> : <BatchFlowLayout currentStep={4}><p>Selecciona un lote desde el historial de carga.</p></BatchFlowLayout>;
}
