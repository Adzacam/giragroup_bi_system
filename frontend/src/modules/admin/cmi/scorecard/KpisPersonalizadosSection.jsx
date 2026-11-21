import React from 'react';
import { SEMAFORO } from '../cmiFormat';

export default function KpisPersonalizadosSection({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div style={{ marginTop: 22 }}>
      <div className="cmi-eyebrow" style={{ marginBottom: 10 }}>
        Indicadores personalizados (fuera de los 23 oficiales · no entran al índice global)
      </div>
      <div className="cmi-kpis">
        {items.map((k) => (
          <article key={k.codigo} className="cmi-card cmi-kpi" style={{ cursor: 'default' }}>
            <div className="cmi-kpi-top">
              <span className="cmi-kpi-code">{k.codigo}</span>
              <span className="cmi-chip cmi-chip-muted">Personalizado</span>
            </div>
            <div className="cmi-kpi-name">{k.nombre}</div>
            <div className="cmi-kpi-val">
              <span className="cmi-num" style={{ fontSize: 22 }}>
                {k.valor !== null && k.valor !== undefined ? k.valor : '—'}
              </span>
              {k.semaforo && k.semaforo !== 'SIN_UMBRAL' && (
                <span className={`cmi-pill ${k.semaforo.toLowerCase()}`}>
                  {SEMAFORO[k.semaforo]?.label || k.semaforo}
                </span>
              )}
            </div>
            {k.meta !== null && k.meta !== undefined && (
              <div className="cmi-kpi-foot"><span>Meta: {k.meta}</span></div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
