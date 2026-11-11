import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import cmiApi from '../../../api/cmiApi';
import usePaginacion from '../../../hooks/usePaginacion';
import Paginacion from '../../../components/shared/Paginacion';
import { SEMAFORO, fmtValor } from './cmiFormat';
import './cmi.css';

function Evolucion({ serie, unidad }) {
  const puntos = serie.filter((s) => s.valor !== null);
  if (puntos.length < 2) return <p className="cmi-kpi-desc">No hay suficientes gestiones con dato para mostrar la evolución.</p>;
  const W = 520, H = 140, P = 24;
  const vals = puntos.map((s) => s.valor);
  const min = Math.min(...vals), max = Math.max(...vals), rango = max - min || 1;
  const x = (i) => P + (i * (W - 2 * P)) / (puntos.length - 1);
  const y = (v) => H - P - ((v - min) / rango) * (H - 2 * P);
  const linea = puntos.map((s, i) => `${i ? 'L' : 'M'}${x(i)},${y(s.valor)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="cmi-evolucion" role="img"
         aria-label={`Evolución de ${puntos[0].gestion} a ${puntos[puntos.length - 1].gestion}`}>
      <path d={linea} fill="none" stroke="var(--color-gira-gold)" strokeWidth="2" />
      {puntos.map((s, i) => (
        <g key={s.gestion}>
          <circle cx={x(i)} cy={y(s.valor)} r="4" fill={(SEMAFORO[s.semaforo] || SEMAFORO.SIN_UMBRAL).color} />
          <text x={x(i)} y={H - 6} textAnchor="middle" className="cmi-evolucion-txt">{s.gestion}</text>
        </g>
      ))}
    </svg>
  );
}

export default function CmiDetalleKpi({ codigo, onClose }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['cmi', 'historial', codigo],
    queryFn: () => cmiApi.getHistorialKpi(codigo),
    staleTime: 60_000,
  });
  const filas = data ? [...data.serie].reverse() : [];
  const pag = usePaginacion(filas);

  useEffect(() => {
    const alTeclear = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [onClose]);

  return (
    <div className="cmi-modal-fondo" onClick={onClose} role="presentation">
      <div className="cmi-card cmi-modal" role="dialog" aria-modal="true" aria-label="Detalle del indicador"
           onClick={(e) => e.stopPropagation()}>
        <button type="button" className="cmi-btn cmi-modal-cerrar" onClick={onClose} aria-label="Cerrar detalle"><X size={16} /></button>
        {isLoading && <div className="cmi-skeleton" style={{ height: 220 }} />}
        {isError && <div className="cmi-error" role="alert">No se pudo cargar el detalle de este indicador.</div>}
        {data && (
          <>
            <div className="cmi-eyebrow">Evolución por gestión</div>
            <h3 style={{ margin: '4px 0 6px' }}>{data.nombre}</h3>
            {data.descripcion && <p className="cmi-kpi-desc">{data.descripcion}</p>}
            <Evolucion serie={data.serie} unidad={data.unidad} />
            <div className="cmi-table-wrap">
              <table className="cmi-table">
                <thead><tr><th>Gestión</th><th>Valor</th><th>Meta</th><th>Estado</th></tr></thead>
                <tbody>
                  {pag.visibles.map((s) => {
                    const sem = SEMAFORO[s.semaforo] || SEMAFORO.SIN_UMBRAL;
                    return (
                      <tr key={s.gestion}>
                        <td>{s.gestion}</td>
                        <td>{fmtValor(s.valor, data.unidad)}</td>
                        <td>{s.meta === null ? 'No definida' : fmtValor(s.meta, data.unidad)}</td>
                        <td><i className="cmi-dot" style={{ background: sem.color }} /> {s.valor === null ? 'Sin dato' : sem.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <Paginacion {...pag} onChange={pag.setPagina} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
