import React from 'react';
import { Search } from 'lucide-react';
import Paginacion from '../../../../components/shared/Paginacion';

export default function Caso2Programas({
  searchProg,
  onSearchChange,
  filtroTipoProg,
  onFiltroTipoChange,
  pagViab,
  onOpenDetail,
}) {
  return (
    <article className="card-mist kinetic-card cmi-pred-card">
      <div className="cmi-pred-card-head">
        <div>
          <span className="cmi-eyebrow">Caso 2 · Foco Comercial / Marketing</span>
          <h3 className="cmi-pred-title">Matriz de Viabilidad Estratégica de Cursos</h3>
        </div>
      </div>

      <div className="cmi-pred-filters">
        <div className="cmi-search-wrap">
          <Search size={14} className="cmi-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="cmi-input cmi-search-input"
            placeholder="Buscar curso o diplomado..."
            aria-label="Buscar curso o diplomado"
            value={searchProg}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
        <select
          className="cmi-input cmi-select-compact"
          aria-label="Filtrar por tipo de programa"
          value={filtroTipoProg}
          onChange={(e) => onFiltroTipoChange(e.target.value)}
        >
          <option value="GLOBAL">Todos los Tipos</option>
          <option value="DIPLOMADO">Diplomados</option>
          <option value="CURSO">Cursos</option>
          <option value="EXPERTO">Expertos</option>
        </select>
      </div>

      <div className="cmi-pred-table-scroll">
        <table className="cmi-pred-table">
          <thead>
            <tr>
              <th scope="col">Programa</th>
              <th scope="col">Total</th>
              <th scope="col">CAGR</th>
              <th scope="col">Proy. 6m</th>
              <th scope="col">Decisión Sugerida</th>
            </tr>
          </thead>
          <tbody>
            {pagViab.visibles.map((p, idx) => (
              <tr
                key={`${p.programa}-${idx}`}
                onClick={() => onOpenDetail({
                  titulo: `Detalle Analítico: ${p.programa}`,
                  tipo: 'caso2_prog',
                  data: p,
                })}
                className="cmi-pred-row"
                title="Haga clic para ver el desglose analítico completo"
              >
                <td className="cmi-pred-prog-cell" title={p.programa}>{p.programa}</td>
                <td className="cmi-mono">{p.total_historico}</td>
                <td className={`cmi-mono ${p.cagr_pct >= 0 ? 'cmi-text-ok' : 'cmi-text-bad'}`}>
                  {p.cagr_pct > 0 ? `+${p.cagr_pct}%` : `${p.cagr_pct}%`}
                </td>
                <td className="cmi-mono cmi-bold">{p.proyeccion_6m} al.</td>
                <td>
                  <span className={`cmi-badge cmi-badge-${p.badge_color || 'amber'}`}>
                    {p.decision_sugerida}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Paginacion {...pagViab} onChange={pagViab.setPagina} />
      </div>
    </article>
  );
}
