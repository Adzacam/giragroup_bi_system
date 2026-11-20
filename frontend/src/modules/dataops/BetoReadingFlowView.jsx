import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams, useLocation } from 'react-router-dom';
import { ArrowRight, BarChart3, Eye, EyeOff } from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import BetoMetricasModal from './components/BetoMetricasModal';
import ProgresoTarea from './components/ProgresoTarea';
import TextoPreparadoTab from './components/TextoPreparadoTab';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import { FILAS_POR_PAGINA } from '../../hooks/usePaginacion';
import { useDraftState, useLoteFlow } from './context/LoteFlowContext';
import useLecturaBeto from './hooks/useLecturaBeto';
import { useRevealCampo } from './hooks/useRevealCi';
import { dataopsApi } from '../../api/dataopsApi';
import { avisarTareaIniciada } from '../../components/shared/TareasSegundoPlano';
import { sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import AnimatedNumberV2 from '../../v2/motion/AnimatedNumberV2';
import AnimatedProgressBarV2 from '../../v2/motion/AnimatedProgressBarV2';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { toDataopsPath } from '../../v2/utils/v2Routes';

const INITIAL = { docId: null, area: 'TODAS', condition: 'ALL', entity: 'TODOS', search: '', page: 1 };
const ESTADOS = { AUTOMATICO: 'Aceptación directa', REVISION: 'En revisión', INCONSISTENCIA: 'Con incidencias' };
const AREAS = { academica: 'Académica', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';
const fmtDec = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2).replace('.', ',') : null;

const ORIGEN_INFO = {
  CI_EXACTA: { label: 'Cédula exacta', bg: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)', bar: 'var(--dataops-success-text)' },
  REGLA_ENCABEZADO: { label: 'Encabezado del archivo', bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', bar: 'var(--color-ink-black)' },
  ENCABEZADO: { label: 'Encabezado del archivo', bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', bar: 'var(--color-ink-black)' },
  FUZZY: { label: 'Coincidencia aproximada', bg: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)', bar: 'var(--dataops-warning-text)' },
  REGEX: { label: 'Patrón', bg: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)', bar: 'var(--color-slate-gray)' },
  BETO: { label: 'Leído por BETO', bg: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', bar: 'var(--color-gira-gold)' },
};

function modeloEtiqueta(entity) {
  const lbl = String(entity?.label || '').toUpperCase();
  if (lbl.includes('ESTUDIANTE')) return 'PER_ESTUDIANTE';
  if (lbl.includes('DOCENTE')) return 'PER_DOCENTE';
  if (lbl.includes('MODULO') || lbl.includes('MÓDULO')) return 'MODULO';
  if (lbl.includes('PROGRAMA')) return 'PROGRAMA';
  if (lbl.includes('CI') || lbl.includes('DOCUMENTO')) return 'CI (por regla)';
  return entity?.tag || entity?.label || 'ENTIDAD';
}

function textoConfianzaEntidad(entity, info) {
  const origen = entity?.origen_confianza || entity?.fuente_resolucion || '';
  const conf = entity?.confianza ?? entity?.betoConfidence;
  if (origen === 'BETO' && conf != null) return `BETO p = ${fmtDec(Number(conf))}`;
  if (origen === 'REGLA_ENCABEZADO' || origen === 'ENCABEZADO') {
    const sim = entity?.detalleConfianza?.similitudEncabezado;
    const val = entity?.detalleConfianza?.validez ?? entity?.detalleConfianza?.catalogo;
    const simTxt = sim != null ? `similitud ${fmtDec(Number(sim))}` : 'encabezado';
    const valTxt = val != null && Number(val) < 0.99 ? `validez ${fmtDec(Number(val))}` : 'valor validado';
    return `Regla por encabezado: ${simTxt} · ${valTxt}`;
  }
  if (conf != null) return `${info.label}: ${fmtDec(Number(conf))}`;
  return info.label;
}

function RegistroBeto({ record }) {
  const { toggleCampo, getValor } = useRevealCampo();
  const [loadingCampo, setLoadingCampo] = useState(null);
  const revealLock = useRef(false);
  const ci = record.ci_enmascarado || record.ci;
  const hasCi = ci && !['No provisto', 'No especificado'].includes(ci);
  const ciRev = getValor(record.id, 'ci');
  const nombreRev = getValor(record.id, 'nombre');
  const correoRev = getValor(record.id, 'correo');
  const rawText = record.raw_text || record.lectura?.texto || '';
  const hasCorreo = Boolean(
    correoRev ||
    record.tiene_correo ||
    (record.correo_enmascarado && !['No provisto', 'No especificado', 'Sin dato'].includes(record.correo_enmascarado)) ||
    rawText.includes('@')
  );
  const reveal = async (campo) => {
    if (revealLock.current) return;
    revealLock.current = true;
    setLoadingCampo(campo);
    try { await toggleCampo(record.id, campo); } finally { revealLock.current = false; setLoadingCampo(null); }
  };
  return <tr>
    <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
      <strong>Fila {record.line_number ?? 'Sin dato'}</strong>
      <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '6px 0' }}>{record.nombre_archivo || 'Sin dato'}</p>
      <p style={{ fontSize: 12 }}>Cédula: {ciRev || (hasCi ? ci : 'Sin dato')}</p>
      {nombreRev && <p style={{ fontSize: 12, marginTop: 4 }}>Nombre: {nombreRev}</p>}
      {correoRev && <p style={{ fontSize: 12, marginTop: 4 }}>Correo: {correoRev}</p>}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
        {hasCi && <Button variant="ghost" onClick={() => reveal('ci')} isLoading={loadingCampo === 'ci'} loadingText="Consultando…" aria-label={ciRev ? 'Ocultar cédula' : 'Revelar cédula con registro de auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
          {ciRev ? <EyeOff size={13} /> : <Eye size={13} />} {ciRev ? 'Ocultar cédula' : 'Revelar con auditoría'}
        </Button>}
        <Button variant="ghost" onClick={() => reveal('nombre')} isLoading={loadingCampo === 'nombre'} loadingText="Consultando…" aria-label={nombreRev ? 'Ocultar nombre' : 'Revelar nombre con auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
          {nombreRev ? <EyeOff size={13} /> : <Eye size={13} />} {nombreRev ? 'Ocultar nombre' : 'Revelar nombre'}
        </Button>
        {hasCorreo && <Button variant="ghost" onClick={() => reveal('correo')} isLoading={loadingCampo === 'correo'} loadingText="Consultando…" aria-label={correoRev ? 'Ocultar correo' : 'Revelar correo con auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
          {correoRev ? <EyeOff size={13} /> : <Eye size={13} />} {correoRev ? 'Ocultar correo' : 'Revelar correo'}
        </Button>}
      </div>
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
        <dl style={{ marginTop: 10 }}>{(record.lectura?.entidades || []).map((entity, index) => {
          const origen = entity.origen_confianza || entity.fuente_resolucion || 'REGLA_ENCABEZADO';
          const info = ORIGEN_INFO[origen] || ORIGEN_INFO.REGLA_ENCABEZADO;
          const confFinal = entity.confianza ?? entity.betoConfidence;
          const lecturaMod = entity.lecturaModelo ?? (origen === 'BETO' ? confFinal : null);
          return <div key={index} style={{ marginTop: 10, paddingTop: 8, borderTop: index > 0 ? '1px solid var(--color-border)' : 'none' }}>
            <dt style={{ fontSize: 12, fontWeight: 600, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
              <span>{String(entity.label || 'Dato').replaceAll('_', ' ').toLocaleLowerCase('es')}</span>
              <span style={{ fontSize: 10.5, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 999, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', color: 'var(--color-ink-black)' }}>{modeloEtiqueta(entity)}</span>
              <span style={{ fontSize: 10.5, padding: '2px 8px', borderRadius: 999, background: info.bg, color: info.color }}>{info.label}</span>
            </dt>
            <dd style={{ fontSize: 12, marginTop: 4 }}>
              {entity.token ?? 'Sin dato'}{entity.matchedCanonical != null && entity.matchedCanonical !== entity.token ? ` · Catálogo: ${entity.matchedCanonical}` : ''}
              <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 3 }}>{textoConfianzaEntidad(entity, info)}</p>
              {(lecturaMod != null || confFinal != null) && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 8, marginTop: 5 }}>
                {lecturaMod != null && <div>
                  <span style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Lectura del modelo ({Math.round(Number(lecturaMod) * 100)} %)</span>
                  <AnimatedProgressBarV2 value={Number(lecturaMod) * 100} color="var(--color-gira-gold)" height={6} ariaLabel="Lectura del modelo" />
                </div>}
                {confFinal != null && <div>
                  <span style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Confianza medida ({Math.round(Number(confFinal) * 100)} %)</span>
                  <AnimatedProgressBarV2 value={Number(confFinal) * 100} color={info.bar} height={6} ariaLabel="Confianza medida" />
                </div>}
              </div>}
            </dd>
          </div>;
        })}</dl>
      </details>
    </td>
  </tr>;
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
  const [metricasOpen, setMetricasOpen] = useState(false);
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
  const pctLectura = data?.tarea?.total
    ? Math.min(100, Math.round(((data.tarea.procesados || 0) / data.tarea.total) * 100))
    : (data?.tarea?.porcentaje ?? 0);
  return <BatchFlowLayout currentStep={2} showReadOnlyContent selectedDocId={filters.docId} onSelectDocId={value => setFilter('docId', value)}>
    <div className="floating-artifact" style={{ padding: 24, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div><h2 className="serif-heading" style={{ fontSize: 20 }}>Lectura de BETO</h2><p style={{ color: 'var(--color-slate-gray)', fontSize: 13, marginTop: 6 }}>BETO identifica los datos de cada fila. Consultar esta página no inicia otro análisis.</p></div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button variant="ghost" type="button" onClick={() => setMetricasOpen(true)} title="Métricas del Modelo BETO">
            <BarChart3 size={15} /> Métricas del Modelo BETO
          </Button>
          {!!batchId && activeTab === 'resultados' && <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={!contexto} onClick={refresh}>Actualizar</Button>}
        </div>
      </div>
      <div role="tablist" aria-label="Vistas de lectura" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
        <Button
          variant="ghost"
          type="button"
          role="tab"
          aria-selected={activeTab === 'resultados'}
          onClick={() => setActiveTab('resultados')}
          style={{
            borderColor: activeTab === 'resultados' ? 'var(--color-gira-gold)' : 'var(--color-border)',
            background: activeTab === 'resultados' ? 'var(--dataops-info-bg)' : undefined,
            color: activeTab === 'resultados' ? 'var(--dataops-info-text)' : undefined,
          }}
        >
          Resultados
        </Button>
        <Button
          variant="ghost"
          type="button"
          role="tab"
          aria-selected={activeTab === 'texto'}
          onClick={() => setActiveTab('texto')}
          style={{
            borderColor: activeTab === 'texto' ? 'var(--color-gira-gold)' : 'var(--color-border)',
            background: activeTab === 'texto' ? 'var(--dataops-info-bg)' : undefined,
            color: activeTab === 'texto' ? 'var(--dataops-info-text)' : undefined,
          }}
        >
          Texto preparado
        </Button>
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
      : !data ? <p className="floating-artifact" role="status" style={{ padding: 24 }}>Consultando resultados…</p>
      : processing ? <ProgresoTarea titulo={`Leyendo… ${pctLectura} %`} tarea={data.tarea} nota="El proceso sigue en segundo plano. Puedes cambiar de página." />
      : !ready ? <div className="floating-artifact" style={{ padding: 24 }}>
        <h3 className="serif-heading" style={{ marginBottom: 10 }}>{data.tarea?.estado === 'ERROR' ? 'La lectura se interrumpió' : 'No hay una lectura guardada disponible'}</h3>
        <p style={{ color: 'var(--color-slate-gray)', marginBottom: 16 }}>{readOnly ? 'Este lote está cerrado. Puedes consultar su resumen en Revisión.' : 'Inicia el análisis para obtener los resultados. Recibirás un aviso al terminar.'}</p>
        {!readOnly && <Button variant="ghost" className="btn-pill-gold" onClick={start} isLoading={starting} loadingText="Iniciando…">{data.tarea?.estado === 'ERROR' ? 'Reintentar lectura' : 'Iniciar lectura de BETO'}</Button>}
      </div> : <>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>{filters.docId ? 'Resumen del archivo seleccionado.' : 'Resumen del lote.'} Los filtros se aplican a la lista de resultados.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 16, marginBottom: 20 }}>
          {[['Analizados', summary?.total_procesados], ['Aceptación directa', summary?.aceptados_automaticamente], ['En revisión', summary?.por_revisar, 'Banda 60–85 % de lectura; el paso ③ agrupa también casos por identidad o catálogo.'], ['Con incidencias', summary?.con_incidencias]].map(([label, value, nota]) => <div className="floating-artifact" key={label} style={{ padding: 18 }}><p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{label}</p><p style={{ fontSize: 25, marginTop: 6 }}>{isFetching ? 'Consultando…' : <AnimatedNumberV2 value={fmt(value)} />}</p>{nota && <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 6, lineHeight: 1.4 }}>{nota}</p>}</div>)}
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
      <Button variant="ghost" onClick={() => navigate(toDataopsPath('/ingesta', location.pathname))}>Volver a carga de archivos</Button>
      {!!batchId && <Button variant="ghost" className="btn-pill-gold" onClick={() => navigate(toDataopsPath(`/lote/${batchId}/revision`, location.pathname))}>Ir a Revisión <ArrowRight size={15} /></Button>}
    </div>
    <BetoMetricasModal isOpen={metricasOpen} onClose={() => setMetricasOpen(false)} />
  </BatchFlowLayout>;
}

export default function BetoReadingFlowView() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const batchId = id || search.get('lote') || localStorage.getItem('last_active_batch_id');
  return <LecturaBeto key={batchId || 'sin-lote'} batchId={batchId} />;
}
