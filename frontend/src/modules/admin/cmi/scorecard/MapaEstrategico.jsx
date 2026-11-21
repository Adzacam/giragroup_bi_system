import React from 'react';
import { ChevronUp } from 'lucide-react';
import { SEMAFORO, bandaIndice, MAPA_ESTRATEGICO } from '../cmiFormat';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';

export default function MapaEstrategico({ perspectivas, activa, onSelect }) {
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
                <div className="cmi-num">{p.indice !== null ? <AnimatedNumberV2 value={p.indice} /> : '—'}</div>
                <span>{p.verdes + p.ambar + p.rojos} de {p.indicadores} evaluados</span>
              </div>
            </button>
          </React.Fragment>
        );
      })}
    </section>
  );
}
