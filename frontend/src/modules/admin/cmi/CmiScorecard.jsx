import React, { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { ArrowUp, ArrowDown, Minus, ChevronUp } from 'lucide-react';
import cmiApi from '../../../api/cmiApi';
import CmiDetalleKpi from './CmiDetalleKpi';
import { SEMAFORO, fmtValor, fmtDelta, bandaIndice, MAPA_ESTRATEGICO } from './cmiFormat';
import './cmi.css';

const ORDEN_SEMAFORO = ['VERDE', 'AMBAR', 'ROJO', 'SIN_UMBRAL'];

function Leyenda() {
  return (
    <div className="cmi-legend" aria-label="Leyenda del semáforo">
      {ORDEN_SEMAFORO.map((s) => (
        <span key={s}><i className="cmi-dot" style={{ background: SEMAFORO[s].color }} />{SEMAFORO[s].label}</span>
      ))}
    </div>
  );
}

function BarraSemaforo({ verdes, ambar, rojos, sin_evaluar }) {
  const total = verdes + ambar + rojos + sin_evaluar || 1;
  const partes = { VERDE: verdes, AMBAR: ambar, ROJO: rojos, SIN_UMBRAL: sin_evaluar };
  return (
    <div className="cmi-stack" role="img"
         aria-label={`${verdes} en meta, ${ambar} en alerta, ${rojos} críticos, ${sin_evaluar} sin evaluar`}>
      {ORDEN_SEMAFORO.filter((s) => partes[s] > 0).map((s) => (
        <i key={s} style={{ width: `${(partes[s] / total) * 100}%`, background: SEMAFORO[s].color }} />
      ))}
    </div>
  );
}

function IndiceGlobal({ global, gestion }) {
  const banda = bandaIndice(global.indice);
  return (
    <section className="cmi-card cmi-global" aria-labelledby="cmi-global-t">
      <div>
        <div className="cmi-eyebrow" id="cmi-global-t">Índice de desempeño · {gestion}</div>
        <div className="cmi-num cmi-global-num" style={{ marginTop: 10 }}>
          {global.indice ?? '—'}{global.indice !== null && <small>/ 100</small>}
        </div>
        <div style={{ marginTop: 8, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
          <i className="cmi-dot" style={{ background: SEMAFORO[banda].color }} />
          {global.indice === null ? 'Sin indicadores evaluables' : SEMAFORO[banda].label}
        </div>
      </div>
      <BarraSemaforo {...global} />
      <div className="cmi-counts">
        {[['VERDE', global.verdes], ['AMBAR', global.ambar], ['ROJO', global.rojos], ['SIN_UMBRAL', global.sin_evaluar]].map(([s, n]) => (
          <div key={s}>
            <b>{n}</b>
            <span><i className="cmi-dot" style={{ background: SEMAFORO[s].color }} />{SEMAFORO[s].label}</span>
          </div>
        ))}
      </div>
      <p className="cmi-kpi-desc">
        Promedio ponderado de las perspectivas. Cada indicador puntúa 100 en meta, 60 en alerta y 20 si es crítico;
        los indicadores sin dato o sin umbral no puntúan.
      </p>
    </section>
  );
}

function MapaEstrategico({ perspectivas, activa, onSelect }) {
  const porCodigo = Object.fromEntries(perspectivas.map((p) => [p.codigo, p]));
  const filas = [...MAPA_ESTRATEGICO].reverse().filter((c) => porCodigo[c]);
  return (
    <section className="cmi-card cmi-map" aria-labelledby="cmi-map-t">
      <div className="cmi-map-head">
        <h3 id="cmi-map-t">Mapa estratégico</h3>
        <span className="cmi-eyebrow">Causa → efecto, de la base a la cima</span>
      </div>
      {filas.map((codigo, i) => {
        const p = porCodigo[codigo];
        const banda = bandaIndice(p.indice);
        return (
          <React.Fragment key={codigo}>
            {i > 0 && <div className="cmi-arrow" aria-hidden="true"><ChevronUp size={14} /></div>}
            <button
              type="button"
              className="cmi-persp-tile"
              aria-current={activa === codigo}
              onClick={() => onSelect(codigo)}
            >
              <i className="bar" style={{ background: SEMAFORO[banda].color }} />
              <div style={{ minWidth: 0 }}>
                <h4>{p.nombre}</h4>
                <p>{p.objetivo}</p>
              </div>
              <div className="cmi-persp-score">
                <div className="cmi-num">{p.indice ?? '—'}</div>
                <span>{p.verdes + p.ambar + p.rojos} de {p.indicadores} evaluados</span>
              </div>
            </button>
          </React.Fragment>
        );
      })}
    </section>
  );
}

function Tendencia({ kpi }) {
  const delta = fmtDelta(kpi.delta, kpi.unidad);
  if (!delta) return null;
  const color = kpi.tendencia === 'MEJORA' ? 'var(--cmi-ok)' : kpi.tendencia === 'EMPEORA' ? 'var(--cmi-bad)' : 'var(--cmi-muted)';
  const Icono = kpi.delta > 0 ? ArrowUp : kpi.delta < 0 ? ArrowDown : Minus;
  return (
    <span className="cmi-trend" style={{ color }} title={`Frente a la gestión anterior (${kpi.tendencia.toLowerCase()})`}>
      <Icono size={13} aria-hidden="true" />{delta}
      <span className="sr-only" style={{ position: 'absolute', left: -9999 }}>
        {kpi.tendencia === 'MEJORA' ? 'mejora' : kpi.tendencia === 'EMPEORA' ? 'empeora' : ''} frente a la gestión anterior
      </span>
    </span>
  );
}

// Avance hacia la meta: para MAX valor/meta; para MIN meta/valor (menos es mejor)
function avance(kpi) {
  const { valor, meta, sentido } = kpi;
  if (valor === null || meta === null || meta === undefined) return null;
  if (sentido === 'MAX') return meta > 0 ? Math.max(0, Math.min(1, valor / meta)) : null;
  if (valor <= meta) return 1;
  return valor > 0 && meta > 0 ? Math.max(0, Math.min(1, meta / valor)) : 0;
}

function TarjetaKpi({ kpi, onAbrir }) {
  const sem = SEMAFORO[kpi.semaforo] || SEMAFORO.SIN_UMBRAL;
  const sinDato = kpi.valor === null;
  const pct = avance(kpi);
  return (
    <article className="cmi-card cmi-kpi" role="button" tabIndex={0}
      onClick={() => onAbrir(kpi.codigo)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onAbrir(kpi.codigo))}
      aria-label={`${kpi.nombre}: ${fmtValor(kpi.valor, kpi.unidad)}, ${sinDato ? 'sin dato' : sem.label}`}>
      <div className="cmi-kpi-top">
        <div style={{ minWidth: 0 }}>
          <div className="cmi-kpi-code">{kpi.codigo}</div>
          <h5>{kpi.nombre}</h5>
        </div>
        <span className="cmi-pill">
          <i className="cmi-dot" style={{ background: sem.color }} />
          {sinDato ? 'Sin dato' : sem.label}
        </span>
      </div>
      <div className="cmi-kpi-value">
        <span className="cmi-num" style={{ color: sinDato ? 'var(--cmi-muted)' : undefined }}>
          {fmtValor(kpi.valor, kpi.unidad, { compacto: true })}
        </span>
        <Tendencia kpi={kpi} />
      </div>
      {pct !== null && (
        <div className="cmi-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100}
             aria-valuenow={Math.round(pct * 100)} aria-label="Avance hacia la meta">
          <i style={{ width: `${pct * 100}%`, background: sem.color }} />
        </div>
      )}
      <div className="cmi-kpi-foot">
        <span>Meta {kpi.meta === null ? 'no definida' : `${kpi.sentido === 'MIN' ? '≤' : '≥'} ${fmtValor(kpi.meta, kpi.unidad, { compacto: true })}`}</span>
        {kpi.valor_anterior !== null && <span>Anterior {fmtValor(kpi.valor_anterior, kpi.unidad, { compacto: true })}</span>}
      </div>
      {(kpi.motivo_sin_dato || kpi.descripcion) && <p className="cmi-kpi-desc">{sinDato && kpi.motivo_sin_dato ? kpi.motivo_sin_dato : kpi.descripcion}</p>}
      <span className="cmi-kpi-ver">Ver evolución</span>
    </article>
  );
}

function SeccionPerspectiva({ p, onAbrir }) {
  const banda = bandaIndice(p.indice);
  return (
    <section className="cmi-section" id={`cmi-${p.codigo}`} aria-labelledby={`cmi-h-${p.codigo}`}>
      <header className="cmi-section-head">
        <div>
          <div className="cmi-eyebrow">Perspectiva · peso {p.peso} %</div>
          <h2 id={`cmi-h-${p.codigo}`}>{p.nombre}</h2>
          <p><strong style={{ fontWeight: 600 }}>Objetivo:</strong> {p.objetivo}</p>
        </div>
        <div className="cmi-section-meta">
          <i className="cmi-dot" style={{ background: SEMAFORO[banda].color }} />
          <span>Índice</span>
          <span className="cmi-num">{p.indice ?? '—'}</span>
        </div>
      </header>
      {p.kpis.length === 0
        ? <div className="cmi-card cmi-empty">No hay indicadores activos en esta perspectiva.</div>
        : <div className="cmi-kpis">{p.kpis.map((k) => <TarjetaKpi key={k.codigo} kpi={k} onAbrir={onAbrir} />)}</div>}
    </section>
  );
}

export default function CmiScorecard() {
  const [gestion, setGestion] = useState(null);
  const [activa, setActiva] = useState(null);
  const [detalle, setDetalle] = useState(null);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['cmi', 'scorecard', gestion],
    queryFn: () => cmiApi.getScorecard(gestion),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

  const irA = (codigo) => {
    setActiva(codigo);
    document.getElementById(`cmi-${codigo}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (isLoading) {
    return (
      <div className="cmi" aria-busy="true">
        <div className="cmi-hero">
          <div className="cmi-skeleton" style={{ height: 320 }} />
          <div className="cmi-skeleton" style={{ height: 320 }} />
        </div>
        <div className="cmi-skeleton" style={{ height: 180 }} />
      </div>
    );
  }
  if (isError) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-error" role="alert">
          No se pudo cargar el Cuadro de Mando Integral.{' '}
          <button className="cmi-btn" style={{ marginLeft: 8 }} onClick={() => refetch()}>Reintentar</button>
        </div>
      </div>
    );
  }
  if (!data?.gestiones?.length) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-empty">Aún no hay datos consolidados en el Data Warehouse para calcular el CMI.</div>
      </div>
    );
  }

  return (
    <div className="cmi" style={{ opacity: isFetching ? 0.7 : 1, transition: 'opacity .2s' }}>
      <div className="cmi-toolbar">
        <div className="cmi-segment" role="group" aria-label="Gestión">
          {data.gestiones.map((g) => (
            <button key={g} type="button" aria-pressed={g === data.gestion} onClick={() => setGestion(g)}>{g}</button>
          ))}
        </div>
        <Leyenda />
      </div>

      <div className="cmi-hero">
        <IndiceGlobal global={data.global} gestion={data.gestion} />
        <MapaEstrategico perspectivas={data.perspectivas} activa={activa} onSelect={irA} />
      </div>

      {data.perspectivas.map((p) => <SeccionPerspectiva key={p.codigo} p={p} onAbrir={setDetalle} />)}
      {detalle && <CmiDetalleKpi codigo={detalle} onClose={() => setDetalle(null)} />}
    </div>
  );
}
