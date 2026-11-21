import React from 'react';
import { SEMAFORO, bandaIndice } from '../cmiFormat';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';
import TarjetaKpi from './TarjetaKpi';

export default function SeccionPerspectiva({ p, onAbrir }) {
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
          <span className="cmi-num">{p.indice !== null ? <AnimatedNumberV2 value={p.indice} /> : '—'}</span>
        </div>
      </header>
      {p.kpis.length === 0
        ? <div className="cmi-card cmi-empty">No hay indicadores activos en esta perspectiva.</div>
        : <div className="cmi-kpis">{p.kpis.map((k) => <TarjetaKpi key={k.codigo} kpi={k} onAbrir={onAbrir} />)}</div>}
    </section>
  );
}
