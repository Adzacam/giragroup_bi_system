import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { X, ChevronDown } from 'lucide-react';
import cmiApi from '../../../api/cmiApi';
import usePaginacion from '../../../hooks/usePaginacion';
import Paginacion from '../../../components/shared/Paginacion';
import { SEMAFORO, fmtValor, fmtDelta } from './cmiFormat';
import AnimatedNumberV2 from '../../../v2/motion/AnimatedNumberV2';
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
      <path d={linea} pathLength="100" className="cmi-evolucion-path" fill="none" stroke="var(--color-gira-gold)" strokeWidth="2" />
      {puntos.map((s, i) => (
        <g key={s.gestion}>
          <circle
            cx={x(i)}
            cy={y(s.valor)}
            r="4"
            className="cmi-evolucion-dot"
            style={{ animationDelay: `${Math.min(i * 75, 650)}ms` }}
            fill={(SEMAFORO[s.semaforo] || SEMAFORO.SIN_UMBRAL).color}
          />
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
  const serie = data?.serie || [];
  const filas = data ? [...serie].reverse().map((s) => {
    const idx = serie.findIndex((item) => item.gestion === s.gestion);
    const prev = idx > 0 ? serie[idx - 1] : null;
    const rowDelta = (s.valor !== null && s.valor !== undefined && prev?.valor !== null && prev?.valor !== undefined)
      ? s.valor - prev.valor
      : null;
    return { ...s, rowDelta };
  }) : [];
  const pag = usePaginacion(filas);

  useEffect(() => {
    const alTeclear = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [onClose]);

  const modalContent = (
    <div className="cmi cmi-modal-fondo" onClick={onClose} role="presentation">
      <div className="cmi-card cmi-modal" role="dialog" aria-modal="true" aria-label="Detalle del indicador"
           onClick={(e) => e.stopPropagation()}>
        <div className="cmi-modal-header">
          <div style={{ minWidth: 0 }}>
            <div className="cmi-eyebrow">Evolución por gestión</div>
            {data && <h3 style={{ margin: '4px 0 0' }}>{data.nombre}</h3>}
          </div>
          <button type="button" className="cmi-btn cmi-modal-cerrar" onClick={onClose} aria-label="Cerrar detalle">
            <X size={16} />
          </button>
        </div>

        {isLoading && <div className="cmi-skeleton" style={{ height: 220 }} />}
        {isError && <div className="cmi-error" role="alert">No se pudo cargar el detalle de este indicador.</div>}
        {data && (
          <>
            {data.descripcion && <p className="cmi-kpi-desc" style={{ marginBottom: 10 }}>{data.descripcion}</p>}
            {['KPI-02', 'KPI-03', 'KPI-12'].includes(String(codigo || '').toUpperCase()) && (
              <p className="cmi-kpi-desc" style={{ marginBottom: 10, fontStyle: 'italic' }}>
                Calculado hasta {data.ultimo_mes_cerrado || 'abril de 2026'} (último mes cerrado de la fuente).
              </p>
            )}
            {(() => {
              const validos = serie.filter((s) => s.valor !== null && s.valor !== undefined);
              if (!validos.length) return null;
              const ultimo = validos[validos.length - 1];
              const anterior = validos.length > 1 ? validos[validos.length - 2] : null;
              const semUltimo = SEMAFORO[ultimo.semaforo] || SEMAFORO.SIN_UMBRAL;
              const brecha = ultimo.meta != null ? ultimo.valor - ultimo.meta : null;
              const delta = anterior ? ultimo.valor - anterior.valor : null;
              const mejor = validos.reduce((best, cur) => (
                data.sentido === 'MIN'
                  ? (cur.valor < best.valor ? cur : best)
                  : (cur.valor > best.valor ? cur : best)
              ), validos[0]);
              const cumplimiento = ultimo.meta != null && ultimo.meta !== 0
                ? (data.sentido === 'MIN'
                    ? (ultimo.valor <= ultimo.meta ? 100 : Math.max(0, (ultimo.meta / ultimo.valor) * 100))
                    : Math.max(0, (ultimo.valor / ultimo.meta) * 100))
                : null;
              const vals = validos.map((v) => v.valor);
              const promedio = vals.reduce((acc, v) => acc + v, 0) / vals.length;
              const minVal = Math.min(...vals);
              const maxVal = Math.max(...vals);

              return (
                <div className="cmi-modal-summary-grid">
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Lectura actual ({ultimo.gestion})</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: semUltimo.color, marginTop: 2 }}>{semUltimo.label}</div>
                  </div>
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Brecha vs. Meta</div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                      {brecha === null ? 'Sin meta' : <AnimatedNumberV2 value={`${brecha >= 0 ? '+' : ''}${fmtValor(brecha, data.unidad)}`} />}
                    </div>
                  </div>
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Variación (Δ)</div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                      {delta === null ? 'N/A' : <AnimatedNumberV2 value={`${delta >= 0 ? '+' : ''}${fmtValor(delta, data.unidad)}`} />}
                    </div>
                  </div>
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Mejor gestión</div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                      {mejor.gestion} · <AnimatedNumberV2 value={fmtValor(mejor.valor, data.unidad)} />
                    </div>
                  </div>
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>% Cumplimiento</div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2, color: semUltimo.color }}>
                      {cumplimiento === null ? 'Sin meta' : <AnimatedNumberV2 value={`${cumplimiento.toFixed(1)} %`} />}
                    </div>
                  </div>
                  <div className="floating-artifact" style={{ padding: '10px 12px', borderRadius: 12 }}>
                    <div style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Promedio / Rango</div>
                    <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>
                      {fmtValor(promedio, data.unidad, { compacto: true })} ({fmtValor(minVal, data.unidad, { compacto: true })}–{fmtValor(maxVal, data.unidad, { compacto: true })})
                    </div>
                  </div>
                </div>
              );
            })()}
            <Evolucion serie={data.serie} unidad={data.unidad} />
            <div className="cmi-table-wrap">
              <table className="cmi-table">
                <thead>
                  <tr>
                    <th>Gestión</th>
                    <th>Valor</th>
                    <th>Meta</th>
                    <th>Variación (Δ)</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {pag.visibles.map((s) => {
                    const sem = SEMAFORO[s.semaforo] || SEMAFORO.SIN_UMBRAL;
                    const deltaTexto = fmtDelta(s.rowDelta, data.unidad) || '—';
                    return (
                      <tr key={s.gestion}>
                        <td>{s.gestion}</td>
                        <td>
                          {fmtValor(s.valor, data.unidad)}
                          {s.n_respuestas != null && (
                            <span style={{ display: 'block', fontSize: 11, color: 'var(--color-slate-gray)', fontVariantNumeric: 'tabular-nums' }}>
                              n = {Number(s.n_respuestas).toLocaleString('es-BO')} resp.
                            </span>
                          )}
                        </td>
                        <td>{s.meta == null ? 'No definida' : fmtValor(s.meta, data.unidad)}</td>
                        <td style={{ fontVariantNumeric: 'tabular-nums' }}>{deltaTexto}</td>
                        <td><i className="cmi-dot" style={{ background: sem.color }} /> {s.valor === null ? 'Sin dato' : sem.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <Paginacion {...pag} onChange={pag.setPagina} />
            </div>

            <details className="cmi-modal-ficha">
              <summary>
                <span>Ficha metodológica del indicador ({data.codigo || codigo})</span>
                <ChevronDown size={15} aria-hidden="true" />
              </summary>
              <div className="cmi-modal-ficha-body">
                <div><strong>Código:</strong> {data.codigo || codigo}</div>
                <div><strong>Unidad:</strong> {data.unidad || '—'}</div>
                <div><strong>Sentido óptimo:</strong> {data.sentido === 'MIN' ? 'Menor es mejor (≤ Meta)' : 'Mayor es mejor (≥ Meta)'}</div>
                <div><strong>Perspectiva:</strong> {data.perspectiva || 'CMI Institucional'}</div>
                {data.formula && <div style={{ gridColumn: '1 / -1' }}><strong>Fórmula:</strong> {data.formula}</div>}
                {data.descripcion && <div style={{ gridColumn: '1 / -1' }}><strong>Definición:</strong> {data.descripcion}</div>}
              </div>
            </details>
          </>
        )}
      </div>
    </div>
  );

  if (typeof document !== 'undefined' && document.body?.appendChild) {
    return createPortal(modalContent, document.body);
  }
  return modalContent;
}
