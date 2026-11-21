import React, { useEffect, useState } from 'react';
import { SEMAFORO, bandaIndice } from '../cmiFormat';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';
import { MOTION_DURATION_MS, MOTION_EASING_CSS, prefersReducedMotion } from '../../../../v2/motion/useCountUpV2';

export const ORDEN_SEMAFORO = ['VERDE', 'AMBAR', 'ROJO', 'SIN_UMBRAL'];

export function Leyenda() {
  return (
    <div className="cmi-legend" aria-label="Leyenda del semáforo">
      {ORDEN_SEMAFORO.map((s) => (
        <span key={s}><i className="cmi-dot" style={{ background: SEMAFORO[s].color }} />{SEMAFORO[s].label}</span>
      ))}
    </div>
  );
}

export function BarraSemaforo({ verdes, ambar, rojos, sin_evaluar }) {
  const total = verdes + ambar + rojos + sin_evaluar || 1;
  const partes = { VERDE: verdes, AMBAR: ambar, ROJO: rojos, SIN_UMBRAL: sin_evaluar };
  const skipMotion = prefersReducedMotion() || typeof requestAnimationFrame === 'undefined';
  const [ready, setReady] = useState(skipMotion);

  useEffect(() => {
    if (skipMotion) {
      setReady(true);
      return undefined;
    }
    let raf2 = null;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => setReady(true));
    });
    return () => {
      cancelAnimationFrame(raf1);
      if (raf2) cancelAnimationFrame(raf2);
    };
  }, [skipMotion, verdes, ambar, rojos, sin_evaluar]);

  return (
    <div
      className="cmi-stack"
      role="img"
      aria-label={`${verdes} en meta, ${ambar} en alerta, ${rojos} críticos, ${sin_evaluar} sin evaluar`}
    >
      {ORDEN_SEMAFORO.filter((s) => partes[s] > 0).map((s) => (
        <i
          key={s}
          style={{
            width: ready ? `${(partes[s] / total) * 100}%` : '0%',
            background: SEMAFORO[s].color,
            transition: skipMotion ? undefined : `width ${MOTION_DURATION_MS}ms ${MOTION_EASING_CSS}`,
          }}
        />
      ))}
    </div>
  );
}

export default function IndiceGlobal({ global, gestion, compact = false }) {
  const banda = bandaIndice(global.indice);
  return (
    <section className={`cmi-card cmi-global ${compact ? 'cmi-global-compact' : ''}`} aria-labelledby="cmi-global-t">
      <div>
        <div className="cmi-eyebrow" id="cmi-global-t">Índice de desempeño · {gestion}</div>
        <div className="cmi-num cmi-global-num" style={{ marginTop: 10 }}>
          {global.indice !== null ? <AnimatedNumberV2 value={global.indice} /> : '—'}
          {global.indice !== null && <small>/ 100</small>}
        </div>
        <div className="cmi-global-status">
          <i className="cmi-dot" style={{ background: SEMAFORO[banda].color }} />
          {global.indice === null ? 'Sin indicadores evaluables' : SEMAFORO[banda].label}
        </div>
      </div>
      <BarraSemaforo {...global} />
      <div className="cmi-counts">
        {[['VERDE', global.verdes], ['AMBAR', global.ambar], ['ROJO', global.rojos], ['SIN_UMBRAL', global.sin_evaluar]].map(([s, n]) => (
          <div key={s}>
            <b><AnimatedNumberV2 value={n} /></b>
            <span><i className="cmi-dot" style={{ background: SEMAFORO[s].color }} />{SEMAFORO[s].label}</span>
          </div>
        ))}
      </div>
      {!compact && (
        <p className="cmi-kpi-desc">
          Promedio ponderado de las perspectivas. Cada indicador puntúa 100 en meta, 60 en alerta y 20 si es crítico;
          los indicadores sin dato o sin umbral no puntúan.
        </p>
      )}
    </section>
  );
}
