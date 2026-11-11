import React, { useEffect, useState } from 'react';
import { HelpCircle, X } from 'lucide-react';
import { GLOSARIO_CMI } from './glosarioTextos';
import './cmi.css';

export default function GlosarioCmi({ tema }) {
  const [abierto, setAbierto] = useState(false);
  const contenido = GLOSARIO_CMI[tema];

  useEffect(() => {
    if (!abierto) return undefined;
    const alTeclear = (e) => e.key === 'Escape' && setAbierto(false);
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [abierto]);

  if (!contenido) return null;
  return (
    <div className="cmi" style={{ display: 'contents' }}>
      <div className="cmi-glosario-barra">
        <button type="button" className="cmi-btn" onClick={() => setAbierto(true)} aria-haspopup="dialog">
          <HelpCircle size={15} aria-hidden="true" /> Ayuda y glosario
        </button>
      </div>
      {abierto && (
        <div className="cmi-modal-fondo" onClick={() => setAbierto(false)} role="presentation">
          <div className="cmi-card cmi-modal" role="dialog" aria-modal="true" aria-label={contenido.titulo}
               onClick={(e) => e.stopPropagation()}>
            <button type="button" className="cmi-btn cmi-modal-cerrar" onClick={() => setAbierto(false)} aria-label="Cerrar ayuda">
              <X size={16} />
            </button>
            <div className="cmi-eyebrow">Ayuda</div>
            <h3 style={{ margin: '4px 0 6px' }}>{contenido.titulo}</h3>
            <p className="cmi-kpi-desc">{contenido.intro}</p>
            <dl className="cmi-glosario">
              {contenido.terminos.map(([termino, definicion]) => (
                <div key={termino}>
                  <dt>{termino}</dt>
                  <dd>{definicion}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}
