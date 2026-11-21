import React from 'react';
import { ArrowRight } from 'lucide-react';
import CardFolderV2 from '../../../../v2/components/CardFolderV2';
import { SEMAFORO, bandaIndice, MAPA_ESTRATEGICO } from '../cmiFormat';

const ORDEN_NUM = {
  APRENDIZAJE: '01',
  PROCESOS_INTERNOS: '02',
  CLIENTES: '03',
  FINANCIERA: '04',
};

export default function MapaHorizontalV2({ perspectivas, activa, onSelect }) {
  const porCodigo = Object.fromEntries(perspectivas.map((p) => [p.codigo, p]));
  const ordenadas = [
    ...MAPA_ESTRATEGICO.filter((c) => porCodigo[c]),
    ...perspectivas.map((p) => p.codigo).filter((c) => !MAPA_ESTRATEGICO.includes(c)),
  ];

  return (
    <section className="cmi-map-horiz-wrap" aria-labelledby="cmi-map-horiz-title">
      <div className="cmi-map-head">
        <h3 id="cmi-map-horiz-title">Mapa estratégico</h3>
        <span className="cmi-eyebrow">Causa → efecto · Aprendizaje a Financiera</span>
      </div>

      <div
        className="cmi-map-horiz-grid"
        role="region"
        aria-label="Perspectivas del mapa estratégico"
      >
        {ordenadas.map((codigo, idx) => {
          const p = porCodigo[codigo];
          const banda = bandaIndice(p.indice);
          const evaluados = p.verdes + p.ambar + p.rojos;
          const isSelected = activa === codigo;
          return (
            <React.Fragment key={codigo}>
              {idx > 0 && (
                <div className="cmi-map-connector" aria-hidden="true">
                  <ArrowRight size={16} />
                </div>
              )}
              <div
                className={`cmi-map-folder-slot ${isSelected ? 'is-selected' : ''}`}
                style={{ '--cmi-stagger': `${idx * 50}ms` }}
              >
                <CardFolderV2
                  code={`${ORDEN_NUM[codigo] || idx + 1} · ${p.peso}%`}
                  title={p.nombre}
                  summary={p.objetivo}
                  badge={p.indice === null ? 'Sin evaluar' : SEMAFORO[banda].label}
                  statusColor={SEMAFORO[banda].color}
                  value={p.indice !== null ? `${p.indice}` : '—'}
                  progress={p.indice !== null ? p.indice / 100 : null}
                  metaText={`${evaluados} de ${p.indicadores} evaluados`}
                  previousText={`${p.verdes}V · ${p.ambar}A · ${p.rojos}R`}
                  onOpen={(el) => onSelect(codigo, el)}
                  className={isSelected ? 'is-active' : ''}
                />
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}
