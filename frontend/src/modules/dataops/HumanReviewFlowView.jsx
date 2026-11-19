import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import BatchFlowLayout from './components/BatchFlowLayout';
import GruposBandeja from './components/GruposBandeja';
import ProgresoTarea from './components/ProgresoTarea';
import IntegridadLote from './components/IntegridadLote';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import { useRevealCampo } from './hooks/useRevealCi';
import useRevision from './hooks/useRevision';
import useRevisionAcciones from './hooks/useRevisionAcciones';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
import AnimatedNumberV2 from '../../v2/motion/AnimatedNumberV2';
import { mensajeError } from '../../utils/mensajeError';
import { textoMotivo } from '../../constants/motivosBandeja';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { toDataopsPath } from '../../v2/utils/v2Routes';

const INITIAL = { docId: null, vista: 'GRUPOS', search: '', area: 'TODAS', page: 1, grupo: null };
const AREAS = { academica: 'Académica', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad', evaluacion_docente: 'Evaluación docente' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';
const FIELD_LIMITS = {
  nota_final: { min: 0, max: 100, step: 'any' },
  mes: { min: 1, max: 12 },
  gestion: { min: 2000, max: 2100 },
  monto_deuda: { min: 0, step: 'any' },
  monto_convenio: { min: 0, step: 'any' },
  cuotas_impagas: { min: 0 },
  numero_modulo: { min: 1 },
};

const initialFieldValue = (item, name) => {
  const estVal = item.estudiante && item.estudiante !== '••••' ? item.estudiante : '';
  const map = {
    nombre_completo: estVal,
    modulo_resuelto: item.modulo_detectado || '',
    nota_final: item.nota_final ?? '',
    monto_deuda: item.monto_deuda ?? '',
    cuotas_impagas: item.cuotas_impagas ?? '',
    mes: item.mes ?? '',
    gestion: item.gestion ?? '',
    programa: item.programa || '',
    programa_resuelto: item.programa || '',
    numero_modulo: item.numero_modulo ?? '',
    codigo_pos: item.codigo_pos || '',
    docente_resuelto: item.docente || '',
    fecha_inscripcion: item.fecha_inscripcion || '',
    categoria_financiera: item.categoria_financiera || '',
    institucion: item.institucion || '',
    clave_convenio: item.clave_convenio || '',
    monto_convenio: item.monto_convenio ?? '',
    escala_respuesta: item.escala_respuesta || '',
  };
  return map[name] ?? '';
};

export function CasoRevision({ item, readOnly, busy, schedule }) {
  const { toggleCampo, getValor } = useRevealCampo();
  const [loadingCampo, setLoadingCampo] = useState(null);
  const revealLock = useRef(false);
  const campos = Array.isArray(item.campos_correccion) ? item.campos_correccion : [];
  const [form, setForm] = useState(() => {
    const init = {};
    for (const c of campos) init[c.name] = initialFieldValue(item, c.name);
    return init;
  });
  const [motivoDescarte, setMotivoDescarte] = useState('');
  const [discard, setDiscard] = useState(false);
  const renderCampo = (c) => {
    const labelText = `${c.label}${c.required ? ' *' : ''}`;
    const aria = `${c.label} del caso ${item.id}`;
    const val = form[c.name] ?? '';
    const onChange = e => setForm(prev => ({ ...prev, [c.name]: e.target.value }));
    if (c.type === 'select' && Array.isArray(c.options)) {
      return <label key={c.name} style={{ fontSize: 12 }}>{labelText}<select aria-label={aria} name={c.name} className="dataops-select" value={val} onChange={onChange} disabled={busy || readOnly} required={Boolean(c.required)}><option value="">Selecciona…</option>{c.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}</select></label>;
    }
    const type = c.type || 'text';
    return <label key={c.name} style={{ fontSize: 12 }}>{labelText}<input aria-label={aria} name={c.name} className="dataops-input" type={type} value={val} onChange={onChange} disabled={busy || readOnly} required={Boolean(c.required)} maxLength={type === 'text' ? 200 : undefined} {...(FIELD_LIMITS[c.name] || {})} /></label>;
  };
  const approve = () => {
    const faltantes = campos.filter(c => c.required && String(form[c.name] ?? '').trim() === '');
    if (faltantes.length > 0) {
      sileoToast.error({
        title: 'Completa los campos obligatorios',
        description: faltantes.map(c => c.label).join(', '),
      });
      return;
    }
    const payload = { accion: 'APROBAR' };
    for (const c of campos) {
      const raw = String(form[c.name] ?? '').trim();
      if (raw !== '') {
        if (c.type === 'number') {
          const num = Number(raw);
          if (!Number.isFinite(num)) {
            sileoToast.error({ title: 'Valor numérico inválido', description: `Revisa el campo ${c.label}.` });
            return;
          }
          payload[c.name] = num;
        } else {
          payload[c.name] = raw;
        }
      }
    }
    schedule(`Aprobar caso ${item.id}`, () => dataopsApi.resolveReviewItem(item.id, payload));
  };
  const reveal = async (campo = 'ci') => {
    if (revealLock.current) return;
    revealLock.current = true;
    setLoadingCampo(campo);
    try { await toggleCampo(item.id, campo); } finally { revealLock.current = false; setLoadingCampo(null); }
  };
  const hasCi = item.ci_enmascarado && !['No provisto', 'No especificado', 'Sin dato'].includes(item.ci_enmascarado);
  const ciRev = getValor(item.id, 'ci');
  const nombreRev = getValor(item.id, 'nombre');
  const correoRev = getValor(item.id, 'correo');
  const hasCorreo = Boolean(
    correoRev ||
    item.tiene_correo ||
    (item.correo_enmascarado && !['No provisto', 'No especificado', 'Sin dato'].includes(item.correo_enmascarado))
  );
  return <details className="floating-artifact" style={{ padding: 18, marginBottom: 12 }}>
    <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}><strong>Caso {item.id}</strong> · {textoMotivo(item.motivo)} · {nombreRev || item.estudiante || 'Sin nombre identificado'}</summary>
    <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '12px 0' }}>{item.archivo_origen || 'Sin archivo'} · {AREAS[item.area] || 'Sin área'} · Índice: {item.indice_registro == null ? 'Sin dato' : `${item.indice_registro} %`}</p>
    <p data-testid={`motivo-detalle-${item.id}`}>{item.motivo_detalle || item.por_que_detuvo}</p>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', margin: '12px 0' }}>
      <span>Cédula: {ciRev || item.ci_enmascarado || 'Sin dato'}</span>
      {hasCi && <Button variant="ghost" isLoading={loadingCampo === 'ci'} loadingText="Consultando…" onClick={() => reveal('ci')}>{ciRev ? 'Ocultar cédula' : 'Revelar con auditoría'}</Button>}
      <span>Nombre: {nombreRev || item.estudiante || '••••'}</span>
      <Button variant="ghost" isLoading={loadingCampo === 'nombre'} loadingText="Consultando…" onClick={() => reveal('nombre')}>{nombreRev ? 'Ocultar nombre' : 'Revelar nombre'}</Button>
      {hasCorreo && <>
        <span>Correo: {correoRev || item.correo_enmascarado || '••••@••••'}</span>
        <Button variant="ghost" isLoading={loadingCampo === 'correo'} loadingText="Consultando…" onClick={() => reveal('correo')}>{correoRev ? 'Ocultar correo' : 'Revelar correo'}</Button>
      </>}
    </div>
    <details style={{ marginBottom: 12 }}><summary style={{ cursor: 'pointer' }}>Ver texto original protegido</summary><p style={{ fontSize: 12, overflowWrap: 'anywhere', padding: '12px 0' }}>{item.que_vio || 'Sin texto disponible'}</p></details>
    {item.sugerencia && <p style={{ marginBottom: 12 }}>Sugerencia guardada: {item.sugerencia}</p>}
    {item.sugerencias_beto?.length > 0 && <div style={{ marginBottom: 12 }}>
      <p style={{ fontSize: 12, marginBottom: 6 }}>Candidatos ordenados por score combinado (similitud y probabilidad de BETO). Solo ordenan: la decisión es tuya.</p>
      <table style={{ width: '100%', fontSize: 12 }}><thead><tr><th align="left">Candidato</th><th align="right">Similitud</th><th align="right">Prob. BETO</th><th align="right">Score</th></tr></thead>
        <tbody>{item.sugerencias_beto.map(s => <tr key={s.id ?? s.nombre}><td>{s.nombre}{s.ci_enmascarado ? ` · ${s.ci_enmascarado}` : ''}</td><td align="right">{(s.similitud * 100).toFixed(0)} %</td><td align="right">{s.probabilidad_beto == null ? 'Sin dato' : `${(s.probabilidad_beto * 100).toFixed(0)} %`}</td><td align="right">{(s.score_combinado * 100).toFixed(0)} %</td></tr>)}</tbody></table>
    </div>}
    {readOnly ? <p>Estado: {item.estado_resolucion === 'DESCARTADO' ? 'Descartado' : item.estado_resolucion === 'RESUELTO_HUMANO' ? 'Resuelto' : 'Pendiente de revisión'}</p> : <>
      {item.manual_presupuesto && <p className="dataops-banner-info">Esta fila requiere revisar su clasificación. La aprobación como persona está bloqueada.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12, margin: '16px 0' }}>
        {campos.map(renderCampo)}
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}><Button disabled={busy || item.locked || item.manual_presupuesto} isLoading={busy} onClick={approve}>Programar aprobación</Button><Button variant="ghost" disabled={busy || item.locked} onClick={() => setDiscard(value => !value)}>Descartar caso</Button></div>
      {item.locked && <p>Otro auditor está revisando este caso.</p>}
      {discard && <div style={{ marginTop: 16 }}><label style={{ fontSize: 12 }}>Motivo del descarte<input aria-label={`Motivo del descarte del caso ${item.id}`} className="dataops-input" type="text" value={motivoDescarte} onChange={e => setMotivoDescarte(e.target.value)} disabled={busy || readOnly} maxLength={200} /></label><p style={{ fontSize: 12, margin: '8px 0' }}>El caso quedará registrado como descartado. Revisa el motivo antes de continuar.</p><Button variant="ghost" disabled={busy || !motivoDescarte.trim()} isLoading={busy} onClick={() => schedule(`Descartar caso ${item.id}`, () => dataopsApi.resolveReviewItem(item.id, { accion: 'DESCARTAR', motivo_descarte: motivoDescarte.trim() }))}>Programar descarte</Button></div>}
    </>}
  </details>;
}

function Revision({ batchId }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { contexto, readOnly } = useLoteFlow();
  const [filters, setFilters] = useDraftState('review.filters.v4', INITIAL);
  const [input, setInput] = useState(filters.search);
  const [exporting, setExporting] = useState(false);
  const exportLock = useRef(false);
  const actions = useRevisionAcciones();
  const { data, error, isFetching, refetch } = useRevision(batchId, filters, !!contexto);
  const { data: summary } = useQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'review-summary', batchId], queryFn: () => dataopsApi.getLoteResumen(batchId), enabled: !!batchId && !!contexto });
  const { data: task } = useQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'review-task', batchId], queryFn: () => dataopsApi.getTareaLote(batchId), enabled: !!batchId && !!contexto, refetchInterval: query => query.state.data?.estado === 'EN_CURSO' ? 2000 : false });
  const { data: prepTask, refetch: refetchPrepTask } = useQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'prep-task', batchId], queryFn: () => dataopsApi.getTareaLote(batchId, 'PREPARACION_REVISION'), enabled: !!batchId && !!contexto, refetchInterval: query => query.state.data?.estado === 'EN_CURSO' ? 2000 : false });
  const preparing = prepTask?.estado === 'EN_CURSO';
  const processing = task?.estado === 'EN_CURSO' || preparing;
  const busy = actions.busy || processing;
  const previousTask = useRef(null);
  const previousPrepTask = useRef(null);
  const prepTriggered = useRef(false);
  useEffect(() => {
    if (previousTask.current === 'EN_CURSO' && task?.estado !== 'EN_CURSO') queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    previousTask.current = task?.estado;
  }, [task?.estado]);
  useEffect(() => {
    const prev = previousPrepTask.current;
    if (
      (prev === 'EN_CURSO' && prepTask?.estado !== 'EN_CURSO')
      || (prepTriggered.current && prev !== 'COMPLETADA' && prepTask?.estado === 'COMPLETADA')
    ) {
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    }
    previousPrepTask.current = prepTask?.estado;
  }, [prepTask?.estado]);
  useEffect(() => {
    if (prepTriggered.current || readOnly || summary?.status !== 'success') return;
    if (prepTask === null && task === null) {
      prepTriggered.current = true;
      dataopsApi.prepararRevision({ id_lote: Number(batchId) })
        .then(res => {
          if (res?.status === 'already_prepared') queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
          return refetchPrepTask();
        })
        .catch(() => { prepTriggered.current = false; });
    }
  }, [batchId, readOnly, summary?.status, prepTask, task, refetchPrepTask]);
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
  return <BatchFlowLayout currentStep={3} showReadOnlyContent selectionDisabled={actions.busy} selectedDocId={filters.docId} onSelectDocId={value => { if (!actions.busy) setFilter('docId', value); }}>
    <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
      <h2 className="serif-heading" style={{ fontSize: 22 }}>Revisión y consolidación</h2>
      <p style={{ fontSize: 13, color: 'var(--color-slate-gray)', margin: '10px 0' }}>Comprueba los casos pendientes. Aprobar un caso guarda su corrección e incorpora el registro; consolidar procesa las filas del lote completo.</p>
      <p style={{ fontSize: 12 }}>85 % o más: directo cuando cumple las reglas · Desde 60 % y menos de 85 %: marcado para revisión · Menos de 60 %: bandeja.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, margin: '16px 0' }}><span>Filas de texto: <strong><AnimatedNumberV2 value={fmt(contexto?.total_registros)} /></strong></span><span>Casos en la selección: <strong>{isFetching ? 'Consultando…' : <AnimatedNumberV2 value={fmt(total)} />}</strong></span><span>Aceptación directa en la lectura: <strong><AnimatedNumberV2 value={fmt(summary?.autoCount)} /></strong></span></div>
      {!readOnly && <Button disabled={busy || summary?.status !== 'success'} isLoading={actions.sending || processing} loadingText="Procesando…" onClick={consolidate}>Consolidar lote</Button>}
      {!readOnly && summary?.status !== 'success' && <p style={{ marginTop: 10 }}>Primero consulta o inicia la lectura de BETO en el paso ②.</p>}
      {readOnly && <p>El lote está cerrado. Las consultas y exportaciones siguen disponibles.</p>}
    </div>
    <IntegridadLote key={batchId} batchId={batchId} />
    {actions.pending.map(op => <div key={op.id} className="dataops-banner-info" role="status" style={{ marginBottom: 12 }}><span>{op.title}: se enviará en {op.seconds} s. Puedes seguir revisando; salir de esta pantalla cancela la espera.</span><Button variant="ghost" onClick={() => actions.cancel(op.id)}>Deshacer</Button></div>)}
    {processing && <ProgresoTarea titulo={preparing ? 'Preparando casos de revisión' : 'Consolidando el lote'} tarea={preparing ? prepTask : task} nota="El proceso continúa en segundo plano y avisará al terminar." />}
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
      {!readOnly && filters.vista === 'PENDIENTES' && !filters.grupo && !filters.search && filters.area === 'TODAS' && <Button variant="ghost" style={{ marginTop: 14 }} disabled={busy || isFetching || !data?.un_clic_total} isLoading={actions.sending} onClick={() => actions.schedule(`Aprobar ${data.un_clic_total} casos con datos completos o coincidencia de nombre`, () => dataopsApi.aprobarCasosUnClic(batchId, filters.docId))}>Aprobar casos verificados ({fmt(data?.un_clic_total)})</Button>}
    </div>
    <div aria-busy={isFetching} className="floating-artifact" style={{ padding: 20 }}>
      {error ? <p role="alert">No se pudo consultar la bandeja. Pulsa Actualizar para reintentarlo.</p> : isFetching || !data ? <p role="status">Consultando casos…</p> : filters.vista === 'GRUPOS' ? <GruposBandeja data={data} readOnly={readOnly} busy={busy} onVerIndividual={clave => { setInput(''); setFilters(prev => ({ ...prev, vista: 'PENDIENTES', grupo: clave, page: 1, search: '', area: 'TODAS' })); }} onResolver={(group, extra = {}) => actions.schedule(`Resolver grupo de ${group.n} casos`, () => dataopsApi.aprobarGrupo({ clave: group.clave, accion: group.accion_grupo, docIds: data.doc_ids, ...extra }))} /> : !data.items?.length ? <p role="status">No hay casos para esta selección.</p> : data.items.map(item => <CasoRevision key={`${item.id}-${filters.vista}`} item={item} readOnly={readOnly || filters.vista === 'RESUELTOS'} busy={busy} schedule={actions.schedule} />)}
      <Paginacion pagina={filters.page} totalPaginas={data?.pagination?.total_pages || 1} total={data?.pagination?.total_items || 0} filasPorPagina={5} disabled={isFetching || actions.busy} onChange={page => setFilters(prev => ({ ...prev, page }))} />
    </div>
    <Button variant="ghost" style={{ marginTop: 20 }} disabled={actions.busy} onClick={() => navigate(toDataopsPath(`/lote/${batchId}/beto`, location.pathname))}>Volver a lectura de BETO</Button>
  </BatchFlowLayout>;
}

export default function HumanReviewFlowView() {
  const { id } = useParams(); const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return batchId ? <Revision key={batchId} batchId={batchId} /> : <BatchFlowLayout currentStep={3}><p>Selecciona un lote desde el historial de carga.</p></BatchFlowLayout>;
}
