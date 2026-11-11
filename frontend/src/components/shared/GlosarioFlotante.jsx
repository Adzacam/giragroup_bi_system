import React, { useEffect, useState } from 'react';
import { HelpCircle, X } from 'lucide-react';

/** Botón "Ayuda y glosario" que abre una ventana flotante con definiciones breves. */
export default function GlosarioFlotante({ contenido }) {
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!abierto) return undefined;
    const alTeclear = (e) => e.key === 'Escape' && setAbierto(false);
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [abierto]);

  if (!contenido) return null;
  return (
    <>
      <div className="glosario-barra">
        <button type="button" className="btn-pill-ghost btn-base glosario-abrir" onClick={() => setAbierto(true)} aria-haspopup="dialog">
          <HelpCircle size={15} aria-hidden="true" /> Ayuda y glosario
        </button>
      </div>
      {abierto && (
        <div className="glosario-fondo" onClick={() => setAbierto(false)} role="presentation">
          <div className="glosario-ventana" role="dialog" aria-modal="true" aria-label={contenido.titulo} onClick={(e) => e.stopPropagation()}>
            <button type="button" className="paginacion-btn glosario-cerrar" onClick={() => setAbierto(false)} aria-label="Cerrar ayuda">
              <X size={16} />
            </button>
            <div className="glosario-etiqueta">Ayuda</div>
            <h3>{contenido.titulo}</h3>
            <p className="glosario-intro">{contenido.intro}</p>
            <dl className="glosario-lista">
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
    </>
  );
}
