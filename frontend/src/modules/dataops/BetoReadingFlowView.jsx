import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams, useLocation } from 'react-router-dom';
import { ArrowRight, BarChart3 } from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import BetoMetricasModal from './components/BetoMetricasModal';
import BetoCascadaResumen from './components/BetoCascadaResumen';
import RegistroBetoRow, { ORIGEN_INFO } from './components/RegistroBetoRow';
import ProgresoTarea from './components/ProgresoTarea';
import TextoPreparadoTab from './components/TextoPreparadoTab';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import useLecturaBeto from './hooks/useLecturaBeto';
import { dataopsApi } from '../../api/dataopsApi';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { confirmar, sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import AnimatedNumberV2 from '../../v2/motion/AnimatedNumberV2';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { toDataopsPath } from '../../v2/utils/v2Routes';

const FILAS_BETO = 20;
const INITIAL = { docId: null, area: 'TODAS', condition: 'ALL', entity: 'TODOS', search: '', page: 1 };
const AREAS = { academica: 'Académica', evaluacion_docente: 'Evaluación docente', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';

function BetoSkeleton() {
  return (
    <div className="floating-artifact" role="status" aria-busy="true" aria-label="Cargando lectura de BETO" style={{ padding: 24, display: 'grid', gap: 12 }}>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} style={{ height: 38, borderRadius: 10, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', opacity: 0.7 }} />
      ))}
    </div>
  );
}

function LecturaBeto({ batchId }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') === 'texto' ? 'texto' : 'resultados';
  const setActiveTab = (nextTab) => {
    const next = new URLSearchParams(searchParams);
    if (nextTab === 'texto') next.set('tab', 'texto');
    else next.delete('tab');
    setSearchParams(next, { replace: true });
  };
  const { contexto, readOnly } = useLoteFlow();
  const [filters, setFilters] = useDraftState('beto.filters.v3', INITIAL);
  const [input, setInput] = useState(filters.search || '');
  const [starting, setStarting] = useState(false);
  const [consolidating, setConsolidating] = useState(false);
  const [cancelingTask, setCancelingTask] = useState(false);
  const [metricasOpen, setMetricasOpen] = useState(false);
  const startLock = useRef(false);
  const { data, error, isFetching, refetch } = useLecturaBeto(batchId, filters, !!contexto || !!batchId);
  const { data: consTask } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'consolidacion-task', String(batchId || '')],
    queryFn: () => dataopsApi.getBatchTask(batchId, 'CONSOLIDACION'),
    enabled: !!batchId,
    refetchInterval: q => q.state.data?.estado === 'EN_CURSO' ? 2000 : false,
  });
  const consPrevRef = useRef(null);
  useEffect(() => {
    if (consPrevRef.current === 'EN_CURSO' && consTask?.estado === 'COMPLETADA') {
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      sileoToast.success({ title: `Lote #${batchId} consolidado`, description: 'Ya puedes abrir Paso 3 para revisar los casos pendientes.' });
    }
    consPrevRef.current = consTask?.estado;
  }, [consTask?.estado, batchId]);
  const processing = data?.status === 'processing';
  const ready = data?.status === 'success';
  const summary = data?.resumen_ejecutivo;
  const pagination = data?.pagination;
  const setFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  useEffect(() => {
    const timer = setTimeout(() => {
      if (input.trim() !== filters.search) setFilters(prev => ({ ...prev, search: input.trim(), page: 1 }));
    }, 300);
    return () => clearTimeout(timer);
  }, [input, filters.search, setFilters]);
  useEffect(() => { if (error) sileoToast.error({ title: 'No se pudo consultar la lectura', description: mensajeError(error, 'Pulsa Actualizar para reintentarlo.') }); }, [error]);
  useEffect(() => {
    if (ready && pagination && filters.page > pagination.total_pages) setFilters(prev => ({ ...prev, page: pagination.total_pages }));
  }, [ready, pagination, filters.page, setFilters]);
  const start = async () => {
    if (startLock.current || readOnly || !batchId) return;
    startLock.current = true;
    setStarting(true);
    try {
      const result = await dataopsApi.startBatchReading(batchId);
      if (result.status === 'processing') avisarTareaIniciada();
      sileoToast.info({ title: result.status === 'ready' ? 'Resultados disponibles' : 'Lectura solicitada', description: result.status === 'ready' ? 'Se mostrarán los resultados guardados.' : 'Puedes seguir usando el sistema. El avance y el resultado aparecerán en las notificaciones.' });
      await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    } catch (err) {
      sileoToast.error({ title: 'No se pudo iniciar la lectura', description: mensajeError(err) });
      if (err.response?.status === 409) queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    } finally { startLock.current = false; setStarting(false); }
  };
  const cancelReading = async () => {
    const tid = data?.tarea?.id;
    if (!tid || cancelingTask) return;
    if (!await confirmar({ title: 'Cancelar lectura en curso', description: 'Se detendrá la lectura de BETO para este lote. Podrás reintentarla o reiniciar el lote.', confirmText: 'Cancelar lectura' })) return;
    setCancelingTask(true);
    try {
      await dataopsApi.cancelarTarea(tid);
      sileoToast.info({ title: 'Lectura cancelada', description: 'La tarea se detuvo. Puedes reintentar o reiniciar el lote.' });
      await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      await refetch();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo cancelar la lectura', description: mensajeError(err) });
    } finally { setCancelingTask(false); }
  };
  const refresh = async () => {
    const result = await refetch();
    if (!result.error) sileoToast.success({ title: 'Lectura actualizada', description: 'Se consultaron los resultados guardados.' });
  };
  const consolidarDesdePaso2 = async () => {
    if (consolidating || readOnly || !batchId) return;
    setConsolidating(true);
    try {
      await dataopsApi.confirmDwInsert({ id_lote: Number(batchId), solo_revision: false, en_segundo_plano: true });
      avisarTareaIniciada();
      sileoToast.info({ title: 'Consolidación iniciada', description: 'Insertando registros al DW y preparando casos pendientes.' });
      await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    } catch (err) {
      sileoToast.error({ title: 'No se pudo iniciar la consolidación', description: mensajeError(err) });
    } finally { setConsolidating(false); }
  };

  return (
    <BatchFlowLayout currentStep={2} showReadOnlyContent selectedDocId={filters.docId} onSelectDocId={value => setFilter('docId', value)}>
      <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div><h2 className="serif-heading" style={{ fontSize: 20 }}>Lectura de BETO</h2><p style={{ color: 'var(--color-slate-gray)', fontSize: 13, marginTop: 6 }}>BETO identifica los datos de cada fila. Consultar esta página no inicia otro análisis.</p></div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', minHeight: 38, flexShrink: 0, alignItems: 'center' }}>
            <Button variant="ghost" type="button" onClick={() => setMetricasOpen(true)} title="Métricas del Modelo BETO" style={{ flexShrink: 0 }}>
              <BarChart3 size={15} /> Métricas del Modelo BETO
            </Button>
            {!!batchId && activeTab === 'resultados' && <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={!contexto} onClick={refresh} style={{ minWidth: 112, flexShrink: 0 }}>Actualizar</Button>}
          </div>
        </div>
        <div role="tablist" aria-label="Vistas de lectura" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
          {[['resultados', 'Resultados'], ['texto', 'Texto preparado']].map(([tabId, label]) => (
            <Button key={tabId} variant="ghost" type="button" role="tab" aria-selected={activeTab === tabId} onClick={() => setActiveTab(tabId)} style={{ borderColor: activeTab === tabId ? 'var(--color-gira-gold)' : 'var(--color-border)', background: activeTab === tabId ? 'var(--dataops-info-bg)' : undefined, color: activeTab === tabId ? 'var(--dataops-info-text)' : undefined }}>
              {label}
            </Button>
          ))}
        </div>
        {activeTab === 'resultados' && (
          <>
            <p style={{ marginTop: 12, fontSize: 12, color: 'var(--color-slate-gray)' }}>85 % o más: directo · 60 % a menos de 85 %: marcado para revisión · Menos de 60 %: bandeja.</p>
            <details style={{ marginTop: 16 }}><summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Cómo se decide el destino de un registro</summary>
              <ul style={{ paddingLeft: 20, marginTop: 10, lineHeight: 1.7 }}>
                <li><strong>85 % o más:</strong> aceptación directa cuando cumple las reglas de validación.</li>
                <li><strong>Desde 60 % y menos de 85 %:</strong> se incorpora marcado para revisión al consolidar.</li>
                <li><strong>Menos de 60 %:</strong> queda en la bandeja para revisión.</li>
              </ul><p style={{ fontSize: 12, marginTop: 8, color: 'var(--color-slate-gray)' }}>Si falta un dato obligatorio o hay una inconsistencia, se requiere revisión aunque el índice alcance el 85 %. La consolidación se realiza en el paso ③.</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginTop: 10, fontSize: 11.5 }}>
                <span style={{ color: 'var(--color-slate-gray)', fontWeight: 600 }}>Cascada de resolución:</span>
                {['CI_EXACTA', 'REGLA_ENCABEZADO', 'FUZZY', 'REGEX', 'BETO'].map((k, i) => (
                  <React.Fragment key={k}>
                    {i > 0 && <span aria-hidden="true" style={{ color: 'var(--color-slate-gray)' }}>→</span>}
                    <span style={{ padding: '2px 8px', borderRadius: 999, background: ORIGEN_INFO[k].bg, color: ORIGEN_INFO[k].color, fontSize: 11 }}>{ORIGEN_INFO[k].label}</span>
                  </React.Fragment>
                ))}
              </div>
            </details>
          </>
        )}
      </div>
      {!batchId ? <p className="floating-artifact" style={{ padding: 24 }}>Selecciona un lote desde el historial de carga.</p>
        : activeTab === 'texto' ? <TextoPreparadoTab batchId={batchId} selectedDocId={filters.docId} context={contexto} />
        : error ? <div className="floating-artifact" role="alert" style={{ padding: 24 }}>No se pudo consultar la lectura. Puedes reintentarlo con Actualizar.</div>
        : !data ? <BetoSkeleton />
        : processing ? <ProgresoTarea titulo="Leyendo registros con BETO…" tarea={data.tarea} nota="El proceso sigue en segundo plano. Puedes cambiar de página." onCancel={data?.tarea?.id ? cancelReading : undefined} canceling={cancelingTask} cancelLabel="Cancelar lectura" />
        : !ready ? <div className="floating-artifact" style={{ padding: 24 }}>
          <h3 className="serif-heading" style={{ marginBottom: 10 }}>{data.tarea?.estado === 'ERROR' ? 'La lectura se interrumpió' : 'No hay una lectura guardada disponible'}</h3>
          <p style={{ color: 'var(--color-slate-gray)', marginBottom: 16 }}>{readOnly ? 'Este lote está cerrado. Puedes consultar su resumen en Revisión.' : 'Inicia el análisis para obtener los resultados. Recibirás un aviso al terminar.'}</p>
          {!readOnly && <Button variant="ghost" className="btn-pill-gold" onClick={start} isLoading={starting} loadingText="Iniciando…">{data.tarea?.estado === 'ERROR' ? 'Reintentar lectura' : 'Iniciar lectura de BETO'}</Button>}
        </div> : <>
          <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>{filters.docId ? 'Resumen del archivo seleccionado.' : 'Resumen del lote.'} Los filtros se aplican a la lista de resultados.</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 16, marginBottom: 20 }}>
            {[['Analizados', summary?.total_procesados], ['Aceptación directa', summary?.aceptados_automaticamente], ['En revisión', summary?.por_revisar, 'Banda 60–85 % de lectura; el paso ③ agrupa también casos por identidad o catálogo.'], ['Con incidencias', summary?.con_incidencias]].map(([label, value, nota]) => <div className="floating-artifact" key={label} style={{ padding: 18 }}><p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{label}</p><p style={{ fontSize: 25, marginTop: 6 }}>{isFetching ? 'Consultando…' : <AnimatedNumberV2 value={fmt(value)} animateOnceKey={`beto-${batchId}-${label}`} />}</p>{nota && <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 6, lineHeight: 1.4 }}>{nota}</p>}</div>)}
          </div>
          <BetoCascadaResumen cascada={data?.resumen_cascada} />
          <div className="floating-artifact" style={{ padding: 20, marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            <label style={{ fontSize: 12 }}>Área<select className="dataops-select" value={filters.area} onChange={e => setFilter('area', e.target.value)} aria-label="Área"><option value="TODAS">Todas</option>{Object.entries(AREAS).map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>
            <label style={{ fontSize: 12 }}>Condición<select className="dataops-select" value={filters.condition} onChange={e => setFilter('condition', e.target.value)} aria-label="Condición">{[['ALL','Todas'],['BAJA_CONFIANZA','Confianza menor al 85 %'],['CONFLICTOS','En revisión o con incidencias'],['CATALOGO','Sin coincidencia en catálogo'],['ABANDONO','Alerta de abandono']].map(([value,text]) => <option value={value} key={value}>{text}</option>)}</select></label>
            <label style={{ fontSize: 12 }}>Dato identificado<select className="dataops-select" value={filters.entity} onChange={e => setFilter('entity', e.target.value)} aria-label="Dato identificado">{[['TODOS','Todos'],['ESTUDIANTE','Estudiante o cédula'],['MODULO','Módulo'],['DOCENTE','Docente'],['CALIFICACION','Nota'],['MONTO','Monto o concepto'],['ASISTENCIA','Asistencia']].map(([value,text]) => <option value={value} key={value}>{text}</option>)}</select></label>
            <label style={{ fontSize: 12, flex: '1 1 220px' }}>Buscar<input className="dataops-select" aria-label="Buscar en la lectura" placeholder="Módulo, archivo o dato del registro" value={input} onChange={e => setInput(e.target.value)} maxLength={200} /></label>
            <Button variant="ghost" onClick={() => { setFilters(INITIAL); setInput(''); }}>Limpiar filtros</Button>
          </div>
          <div className="floating-artifact" style={{ padding: 20 }} aria-busy={isFetching}>
            {isFetching ? <BetoSkeleton /> : <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Resultados de lectura BETO"><table className="dataops-table" style={{ width: '100%', tableLayout: 'fixed', textAlign: 'left' }}><thead><tr><th>Fila y documento</th><th>Módulo o concepto</th><th style={{ width: 100 }}>Índice</th><th>Resultado</th></tr></thead><tbody>{(data.registros || []).map(record => <RegistroBetoRow key={record.id} record={record} />)}</tbody></table>{!data.registros?.length && <p role="status" style={{ padding: 20 }}>No se encontraron registros para estos filtros.</p>}</div>}
            <Paginacion pagina={filters.page} totalPaginas={pagination?.total_pages || 1} total={pagination?.total_items || 0} filasPorPagina={FILAS_BETO} disabled={isFetching} onChange={value => setFilters(prev => ({ ...prev, page: value }))} />
          </div>
        </>}
      {consTask?.estado === 'EN_CURSO' && <div style={{ marginTop: 16 }}><ProgresoTarea titulo="Consolidando lote al DW…" tarea={consTask} nota="Insertando hechos y preparando bandeja HITL." /></div>}
      {consTask?.estado === 'COMPLETADA' && (
        <div className="dataops-banner-info" role="status" style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span>Consolidación completada para el lote #{batchId}.</span>
          <Button variant="ghost" className="btn-pill-gold" onClick={() => navigate(toDataopsPath(`/lote/${batchId}/revision?vista=PENDIENTES`, location.pathname))}>Ir a Revisión <ArrowRight size={15} /></Button>
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginTop: 20 }}>
        <Button variant="ghost" onClick={() => navigate(toDataopsPath('/ingesta', location.pathname))}>Volver a carga de archivos</Button>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {!!batchId && ready && !readOnly && consTask?.estado !== 'EN_CURSO' && (
            <Button variant="ghost" onClick={consolidarDesdePaso2} isLoading={consolidating} loadingText="Consolidando…">Consolidar / Insertar al DW</Button>
          )}
          {!!batchId && <Button variant="ghost" className="btn-pill-gold" onClick={() => navigate(toDataopsPath(`/lote/${batchId}/revision?vista=PENDIENTES`, location.pathname))}>Ir a Revisión <ArrowRight size={15} /></Button>}
        </div>
      </div>
      <BetoMetricasModal isOpen={metricasOpen} onClose={() => setMetricasOpen(false)} />
    </BatchFlowLayout>
  );
}

export default function BetoReadingFlowView() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return <LecturaBeto key={batchId || 'sin-lote'} batchId={batchId} />;
}
