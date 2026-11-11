import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function Paginacion({ pagina, totalPaginas, total, filasPorPagina, onChange }) {
  if (total <= filasPorPagina) return null;
  const desde = (pagina - 1) * filasPorPagina + 1;
  const hasta = Math.min(pagina * filasPorPagina, total);
  return (
    <nav className="paginacion" aria-label="Paginación de la tabla">
      <span className="paginacion-resumen">{desde}–{hasta} de {total}</span>
      <div className="paginacion-controles">
        <button type="button" className="paginacion-btn" disabled={pagina <= 1}
          onClick={() => onChange(pagina - 1)} aria-label="Página anterior">
          <ChevronLeft size={16} />
        </button>
        <span className="paginacion-pagina">Página {pagina} de {totalPaginas}</span>
        <button type="button" className="paginacion-btn" disabled={pagina >= totalPaginas}
          onClick={() => onChange(pagina + 1)} aria-label="Página siguiente">
          <ChevronRight size={16} />
        </button>
      </div>
    </nav>
  );
}
