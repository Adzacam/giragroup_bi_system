import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';
import { SEMAFORO, fmtValor, fmtDelta } from '../cmiFormat';
import CardFolderV2 from '../../../../v2/components/CardFolderV2';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';
import AnimatedProgressBarV2 from '../../../../v2/motion/AnimatedProgressBarV2';

export function isV2Active() {
  if (typeof document !== 'undefined' && document.documentElement.getAttribute('data-ui-version') === 'v2') {
    return true;
  }
  if (typeof window !== 'undefined' && window.location?.pathname?.startsWith('/v2')) {
    return true;
  }
  return false;
}

export function Tendencia({ kpi }) {
  const delta = fmtDelta(kpi.delta, kpi.unidad);
  if (!delta) return null;
  const color = kpi.tendencia === 'MEJORA' ? 'var(--cmi-ok)' : kpi.tendencia === 'EMPEORA' ? 'var(--cmi-bad)' : 'var(--cmi-muted)';
  const Icono = kpi.delta > 0 ? ArrowUp : kpi.delta < 0 ? ArrowDown : Minus;
  return (
    <span className="cmi-trend" style={{ color }} title={`Frente a la gestión anterior (${kpi.tendencia.toLowerCase()})`}>
      <Icono size={13} aria-hidden="true" />{delta}
      <span className="sr-only">
        {kpi.tendencia === 'MEJORA' ? 'mejora' : kpi.tendencia === 'EMPEORA' ? 'empeora' : ''} frente a la gestión anterior
      </span>
    </span>
  );
}

// Avance hacia la meta: para MAX valor/meta; para MIN meta/valor (menos es mejor)
export function avance(kpi) {
  const { valor, meta, sentido } = kpi;
  if (valor === null || meta === null || meta === undefined) return null;
  if (sentido === 'MAX') return meta > 0 ? Math.max(0, Math.min(1, valor / meta)) : null;
  if (valor <= meta) return 1;
  return valor > 0 && meta > 0 ? Math.max(0, Math.min(1, meta / valor)) : 0;
}

export default function TarjetaKpi({ kpi, onAbrir, forceClassicCard = false }) {
  const sem = SEMAFORO[kpi.semaforo] || SEMAFORO.SIN_UMBRAL;
  const sinDato = kpi.valor === null;
  const pct = avance(kpi);

  const tieneRespuestas = kpi.n_respuestas !== null && kpi.n_respuestas !== undefined;
  const textoRespuestas = tieneRespuestas
    ? `n = ${Number(kpi.n_respuestas).toLocaleString('es-BO')} resp.`
    : null;

  if (isV2Active() && !forceClassicCard) {
    const metaText = kpi.meta === null
      ? 'Meta no definida'
      : `Meta ${kpi.sentido === 'MIN' ? '≤' : '≥'} ${fmtValor(kpi.meta, kpi.unidad, { compacto: true })}`;
    const basePrev = kpi.valor_anterior !== null && kpi.valor_anterior !== undefined
      ? `Anterior ${fmtValor(kpi.valor_anterior, kpi.unidad, { compacto: true })}`
      : 'Sin gestión anterior';
    const previousText = textoRespuestas ? `${basePrev} · ${textoRespuestas}` : basePrev;
    return (
      <CardFolderV2
        code={kpi.codigo}
        title={kpi.nombre}
        summary={sinDato && kpi.motivo_sin_dato ? kpi.motivo_sin_dato : kpi.descripcion}
        badge={sinDato ? 'Sin dato' : sem.label}
        statusColor={sem.color}
        value={fmtValor(kpi.valor, kpi.unidad, { compacto: true })}
        trend={<Tendencia kpi={kpi} />}
        progress={pct}
        metaText={metaText}
        previousText={previousText}
        onOpen={() => onAbrir(kpi.codigo)}
      />
    );
  }

  return (
    <article
      className="cmi-card cmi-kpi"
      role="button"
      tabIndex={0}
      onClick={() => onAbrir(kpi.codigo)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onAbrir(kpi.codigo))}
      aria-label={`${kpi.nombre}: ${fmtValor(kpi.valor, kpi.unidad)}, ${sinDato ? 'sin dato' : sem.label}`}
    >
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
          <AnimatedNumberV2 value={fmtValor(kpi.valor, kpi.unidad, { compacto: true })} />
        </span>
        <Tendencia kpi={kpi} />
      </div>
      {pct !== null && (
        <AnimatedProgressBarV2
          className="cmi-progress"
          value={pct * 100}
          max={100}
          color={sem.color}
          ariaLabel="Avance hacia la meta"
        />
      )}
      <div className="cmi-kpi-foot">
        <span>Meta {kpi.meta === null ? 'no definida' : `${kpi.sentido === 'MIN' ? '≤' : '≥'} ${fmtValor(kpi.meta, kpi.unidad, { compacto: true })}`}</span>
        {kpi.valor_anterior !== null && <span>Anterior {fmtValor(kpi.valor_anterior, kpi.unidad, { compacto: true })}</span>}
        {textoRespuestas && <span className="cmi-kpi-n-respuestas">{textoRespuestas}</span>}
      </div>
      {(kpi.motivo_sin_dato || kpi.descripcion) && (
        <p className="cmi-kpi-desc">{sinDato && kpi.motivo_sin_dato ? kpi.motivo_sin_dato : kpi.descripcion}</p>
      )}
      <span className="cmi-kpi-ver">Ver evolución</span>
    </article>
  );
}
