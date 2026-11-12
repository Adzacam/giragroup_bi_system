import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import ProgresoTarea from './components/ProgresoTarea';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { FILAS_POR_PAGINA } from '../../hooks/usePaginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import useLecturaBeto from './hooks/useLecturaBeto';
import { useRevealCi } from './hooks/useRevealCi';
import { dataopsApi } from '../../api/dataopsApi';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';

const INITIAL = { docId: null, area: 'TODAS', condition: 'ALL', entity: 'TODOS', search: '', page: 1 };
const ESTADOS = { AUTOMATICO: 'Aceptación directa', REVISION: 'En revisión', INCONSISTENCIA: 'Con incidencias' };
const AREAS = { academica: 'Académica', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';

function RegistroBeto({ record }) {
  const [revealed, toggleCi] = useRevealCi();
  const [revealing, setRevealing] = useState(false);
  const revealLock = useRef(false);
  const ci = record.ci_enmascarado || record.ci;
  const hasCi = ci && !['No provisto', 'No especificado'].includes(ci);
  const reveal = async () => {
    if (revealLock.current) return;
    revealLock.current = true;
    setRevealing(true);
    try { await toggleCi(record.id); } finally { revealLock.current = false; setRevealing(false); }
  };
  return <tr>
    <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
      <strong>Fila {record.line_number ?? 'Sin dato'}</strong>
      <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '6px 0' }}>{record.nombre_archivo || 'Sin dato'}</p>
      <p style={{ fontSize: 12 }}>Cédula: {revealed[record.id] || (hasCi ? ci : 'Sin dato')}</p>
      {hasCi && <Button variant="ghost" onClick={reveal} isLoading={revealing} loadingText="Consultando…" aria-label={revealed[record.id] ? 'Ocultar cédula' : 'Revelar cédula con registro de auditoría'} style={{ marginTop: 6, padding: '4px 10px', fontSize: 11 }}>
        {revealed[record.id] ? <EyeOff size={13} /> : <Eye size={13} />} {revealed[record.id] ? 'Ocultar' : 'Revelar con auditoría'}
      </Button>}
    </td>
    <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
      <p>{record.modulo && record.modulo !== 'No detectado' ? record.modulo : 'Sin módulo o concepto identificado'}</p>
      <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginTop: 6 }}>{AREAS[record.area] || 'Sin dato'}</p>
      {record.nota_normalizada != null && <p style={{ marginTop: 6 }}>Nota: {record.nota_normalizada}/100</p>}
      {record.monto != null && <p style={{ marginTop: 6 }}>Monto: {record.monto}</p>}
    </td>
    <td style={{ verticalAlign: 'top', fontVariantNumeric: 'tabular-nums' }}>{record.indice_registro == null ? 'Sin dato' : `${fmt(record.indice_registro)} %`}</td>
    <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
      <strong style={{ color: record.estado === 'AUTOMATICO' ? 'var(--dataops-success-text)' : 'var(--dataops-warning-text)' }}>{ESTADOS[record.estado] || 'Sin dato'}</strong>
      <details style={{ marginTop: 10 }}>
        <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Ver explicación y datos identificados</summary>
        <p style={{ marginTop: 10 }}>{record.decision?.motivo_llano || 'Sin observaciones adicionales.'}</p>
        <p style={{ marginTop: 10, fontSize: 12, color: 'var(--color-slate-gray)' }}>{record.raw_text || record.lectura?.texto || 'Sin texto disponible'}</p>
        <dl style={{ marginTop: 10 }}>{(record.lectura?.entidades || []).map((entity, index) => <div key={index} style={{ marginTop: 8 }}>
          <dt style={{ fontSize: 12, fontWeight: 600 }}>{String(entity.label || 'Dato').replaceAll('_', ' ').toLocaleLowerCase('es')}</dt>
          <dd style={{ fontSize: 12 }}>{entity.token ?? 'Sin dato'}{entity.matchedCanonical != null && entity.matchedCanonical !== entity.token ? ` · Catálogo: ${entity.matchedCanonical}` : ''}</dd>
        </div>)}</dl>
      </details>
    </td>
  </tr>;
}

function LecturaBeto({ batchId }) {
  const navigate = useNavigate();
  const { contexto, readOnly } = useLoteFlow();
  const [filters, setFilters] = useDraftState('beto.filters.v3', INITIAL);
  const [input, setInput] = useState(filters.search || '');
  const [starting, setStarting] = useState(false);
  const startLock = useRef(false);
  const { data, error, isFetching, refetch } = useLecturaBeto(batchId, filters, !!contexto);
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
    }
    finally { startLock.current = false; setStarting(false); }
  };
  const refresh = async () => {
    const result = await refetch();
    if (!result.error) sileoToast.success({ title: 'Lectura actualizada', description: 'Se consultaron los resultados guardados.' });
  };
  return <BatchFlowLayout currentStep={3} showReadOnlyContent selectedDocId={filters.docId} onSelectDocId={value => setFilter('docId', value)}>
    <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div><h2 className="serif-heading" style={{ fontSize: 20 }}>Resultados de la lectura</h2><p style={{ color: 'var(--color-slate-gray)', fontSize: 13, marginTop: 6 }}>BETO identifica los datos de cada fila. Consultar esta página no inicia otro análisis.</p></div>
        {!!batchId && <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={!contexto} onClick={refresh}>Actualizar</Button>}
      </div>
      <p style={{ marginTop: 12, fontSize: 12, color: 'var(--color-slate-gray)' }}>85 % o más: directo · 60 % a menos de 85 %: marcado para revisión · Menos de 60 %: bandeja.</p>
      <details style={{ marginTop: 16 }}><summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Cómo se decide el destino de un registro</summary>
        <ul style={{ paddingLeft: 20, marginTop: 10, lineHeight: 1.7 }}>
          <li><strong>85 % o más:</strong> aceptación directa cuando cumple las reglas de validación.</li>
          <li><strong>Desde 60 % y menos de 85 %:</strong> se incorpora marcado para revisión al consolidar.</li>
          <li><strong>Menos de 60 %:</strong> queda en la bandeja para revisión.</li>
        </ul><p style={{ fontSize: 12, marginTop: 8, color: 'var(--color-slate-gray)' }}>Si falta un dato obligatorio o hay una inconsistencia, se requiere revisión aunque el índice alcance el 85 %. La consolidación se realiza en el paso ④.</p>
      </details>
    </div>
    {!batchId ? <p className="floating-artifact" style={{ padding: 24 }}>Selecciona un lote desde el historial de carga.</p>
      : error ? <div className="floating-artifact" role="alert" style={{ padding: 24 }}>No se pudo consultar la lectura. Puedes reintentarlo con Actualizar.</div>
      : !data ? <p className="floating-artifact" role="status" style={{ padding: 24 }}>Consultando resultados…</p>
      : processing ? <ProgresoTarea titulo="BETO está analizando el lote" tarea={data.tarea} nota="El proceso sigue en segundo plano. Puedes cambiar de página." />
      : !ready ? <div className="floating-artifact" style={{ padding: 24 }}>
        <h3 className="serif-heading" style={{ marginBottom: 10 }}>{data.tarea?.estado === 'ERROR' ? 'La lectura se interrumpió' : 'No hay una lectura guardada disponible'}</h3>
        <p style={{ color: 'var(--color-slate-gray)', marginBottom: 16 }}>{readOnly ? 'Este lote está cerrado. Puedes consultar su resumen en Revisión.' : 'Inicia el análisis para obtener los resultados. Recibirás un aviso al terminar.'}</p>
        {!readOnly && <Button variant="ghost" className="btn-pill-gold" onClick={start} isLoading={starting} loadingText="Iniciando…">{data.tarea?.estado === 'ERROR' ? 'Reintentar lectura' : 'Iniciar lectura de BETO'}</Button>}
      </div> : <>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>{filters.docId ? 'Resumen del archivo seleccionado.' : 'Resumen del lote.'} Los filtros se aplican a la lista de resultados.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 16, marginBottom: 20 }}>
          {[['Analizados', summary?.total_procesados], ['Aceptación directa', summary?.aceptados_automaticamente], ['En revisión', summary?.por_revisar], ['Con incidencias', summary?.con_incidencias]].map(([label, value]) => <div className="floating-artifact" key={label} style={{ padding: 18 }}><p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{label}</p><p style={{ fontSize: 25, marginTop: 6 }}>{isFetching ? 'Consultando…' : fmt(value)}</p></div>)}
        </div>
        <div className="floating-artifact" style={{ padding: 20, marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <label style={{ fontSize: 12 }}>Área<select className="dataops-select" value={filters.area} onChange={e => setFilter('area', e.target.value)} aria-label="Área"><option value="TODAS">Todas</option>{Object.entries(AREAS).map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>
          <label style={{ fontSize: 12 }}>Condición<select className="dataops-select" value={filters.condition} onChange={e => setFilter('condition', e.target.value)} aria-label="Condición">{[['ALL','Todas'],['BAJA_CONFIANZA','Confianza menor al 85 %'],['CONFLICTOS','En revisión o con incidencias'],['CATALOGO','Sin coincidencia en catálogo'],['ABANDONO','Alerta de abandono']].map(([value,text]) => <option value={value} key={value}>{text}</option>)}</select></label>
          <label style={{ fontSize: 12 }}>Dato identificado<select className="dataops-select" value={filters.entity} onChange={e => setFilter('entity', e.target.value)} aria-label="Dato identificado">{[['TODOS','Todos'],['ESTUDIANTE','Estudiante o cédula'],['MODULO','Módulo'],['DOCENTE','Docente'],['CALIFICACION','Nota'],['MONTO','Monto o concepto'],['ASISTENCIA','Asistencia']].map(([value,text]) => <option value={value} key={value}>{text}</option>)}</select></label>
          <label style={{ fontSize: 12, flex: '1 1 220px' }}>Buscar<input className="dataops-select" aria-label="Buscar en la lectura" placeholder="Módulo, archivo o dato del registro" value={input} onChange={e => setInput(e.target.value)} maxLength={200} /></label>
          <Button variant="ghost" onClick={() => { setFilters(INITIAL); setInput(''); }}>Limpiar filtros</Button>
        </div>
        <div className="floating-artifact" style={{ padding: 20 }} aria-busy={isFetching}>
          {isFetching ? <p role="status">Cargando página {filters.page}…</p> : <div style={{ overflowX: 'auto' }}><table className="dataops-table" style={{ width: '100%', tableLayout: 'fixed', textAlign: 'left' }}><thead><tr><th>Fila y documento</th><th>Módulo o concepto</th><th style={{ width: 100 }}>Índice</th><th>Resultado</th></tr></thead><tbody>{(data.registros || []).map(record => <RegistroBeto key={record.id} record={record} />)}</tbody></table>{!data.registros?.length && <p role="status" style={{ padding: 20 }}>No se encontraron registros para estos filtros.</p>}</div>}
          <Paginacion pagina={filters.page} totalPaginas={pagination?.total_pages || 1} total={pagination?.total_items || 0} filasPorPagina={FILAS_POR_PAGINA} disabled={isFetching} onChange={value => setFilters(prev => ({ ...prev, page: value }))} />
        </div>
      </>}
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginTop: 20 }}>
      <Button variant="ghost" disabled={!batchId} onClick={() => navigate(batchId ? `/dataops/lote/${batchId}/texto` : '/dataops/ingesta')}>Volver a texto preparado</Button>
      {!!batchId && <Button variant="ghost" className="btn-pill-gold" onClick={() => navigate(`/dataops/lote/${batchId}/revision`)}>Ir a Revisión <ArrowRight size={15} /></Button>}
    </div>
  </BatchFlowLayout>;
}

export default function BetoReadingFlowView() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return <LecturaBeto key={batchId || 'sin-lote'} batchId={batchId} />;
}
