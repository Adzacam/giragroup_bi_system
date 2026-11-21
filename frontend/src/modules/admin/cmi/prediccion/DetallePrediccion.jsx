import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { fmtBs } from './chartConfig';

export default function DetallePrediccion({ modalDetail, onClose }) {
  const closeBtnRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!modalDetail) return undefined;
    triggerRef.current = modalDetail.triggerEl || document.activeElement;
    closeBtnRef.current?.focus();

    const onKey = (e) => {
      if (e.key === 'Escape') {
        onClose();
        triggerRef.current?.focus?.();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [modalDetail, onClose]);

  const handleClose = () => {
    onClose();
    triggerRef.current?.focus?.();
  };

  if (!modalDetail) return null;

  const drawerNode = (
    <div className="cmi-drawer-backdrop" onClick={handleClose}>
      <aside
        className="cmi-card cmi-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cmi-pred-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="cmi-modal-header">
          <h3 id="cmi-pred-drawer-title" className="cmi-pred-modal-title">
            {modalDetail.titulo}
          </h3>
          <button
            ref={closeBtnRef}
            type="button"
            className="cmi-btn cmi-modal-cerrar"
            onClick={handleClose}
            aria-label="Cerrar panel lateral"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {modalDetail.tipo === 'caso1' && modalDetail.data && (
          <div>
            <p className="cmi-pred-modal-desc">
              Serie histórica mensual de alumnos matriculados ({modalDetail.data?.periodos_historicos?.[0]} – {modalDetail.data?.periodos_historicos?.at(-1)}, N={modalDetail.data?.n_observaciones} meses),
              junto con las proyecciones Holt-Winters amortiguado (m=12) con IC 95%.
            </p>
            <div className="cmi-pred-table-scroll cmi-pred-table-scroll-lg">
              <table className="cmi-pred-table">
                <thead>
                  <tr>
                    <th scope="col">Periodo</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Valor</th>
                    <th scope="col">IC 95% Inf</th>
                    <th scope="col">IC 95% Sup</th>
                  </tr>
                </thead>
                <tbody>
                  {modalDetail.data.periodos_historicos.map((p, i) => (
                    <tr key={i}>
                      <td className="cmi-mono">{p}</td>
                      <td className="cmi-muted">Histórico Real</td>
                      <td className="cmi-bold">{modalDetail.data.valores_historicos[i]} alumnos</td>
                      <td className="cmi-muted">-</td>
                      <td className="cmi-muted">-</td>
                    </tr>
                  ))}
                  {modalDetail.data.periodos_proyectados.map((p, i) => (
                    <tr key={`p-${i}`} className="cmi-pred-row-proy">
                      <td className="cmi-mono cmi-bold cmi-text-gold">{p} (Proy)</td>
                      <td className="cmi-bold cmi-text-gold">Holt-Winters</td>
                      <td className="cmi-bold">{modalDetail.data.forecast_hw[i]} alumnos</td>
                      <td className="cmi-mono">{modalDetail.data.ic_lower_95[i]}</td>
                      <td className="cmi-mono">{modalDetail.data.ic_upper_95[i]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {modalDetail.tipo === 'caso2_prog' && modalDetail.data && (
          <div>
            <div className="cmi-pred-chips">
              <span className="cmi-chip cmi-chip-muted">{modalDetail.data.tipo}</span>
              <span className={`cmi-badge cmi-badge-${modalDetail.data.badge_color || 'amber'}`}>
                {modalDetail.data.decision_sugerida}
              </span>
            </div>
            <div className="cmi-pred-justif">
              <div className="cmi-pred-justif-title">Dictamen Estratégico y Justificación de Marketing:</div>
              <div className="cmi-pred-justif-body">{modalDetail.data.justificacion}</div>
            </div>
            <div className="cmi-modal-summary-grid">
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Inscritos Totales</span>
                <strong className="cmi-mono">{modalDetail.data.total_historico}</strong>
                <small>Matrícula histórica</small>
              </div>
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Inscritos {modalDetail.data.anio_anterior}</span>
                <strong className="cmi-mono">{modalDetail.data.inscritos_anio_anterior}</strong>
                <small>Última gestión cerrada</small>
              </div>
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Inscritos {modalDetail.data.anio_actual}</span>
                <strong className="cmi-mono">{modalDetail.data.inscritos_anio_actual}</strong>
                <small>Gestión en curso</small>
              </div>
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Tasa CAGR</span>
                <strong className={`cmi-mono ${modalDetail.data.cagr_pct >= 0 ? 'cmi-text-ok' : 'cmi-text-bad'}`}>
                  {modalDetail.data.cagr_pct > 0 ? `+${modalDetail.data.cagr_pct}%` : `${modalDetail.data.cagr_pct}%`}
                </strong>
                <small>Crecimiento anual</small>
              </div>
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Proyección 6 Meses</span>
                <strong className="cmi-mono cmi-text-gold">{modalDetail.data.proyeccion_6m} al.</strong>
                <small>Absorción estimada</small>
              </div>
              <div className="cmi-pred-stat">
                <span className="cmi-eyebrow">Pendiente OLS</span>
                <strong className="cmi-mono">{modalDetail.data.tendencia_ols}</strong>
                <small>Ritmo de absorción</small>
              </div>
            </div>
          </div>
        )}

        {modalDetail.tipo === 'caso3' && modalDetail.data && (
          <div>
            <p className="cmi-pred-modal-desc">
              Comparativa presupuestaria mensual: Meta de Catálogo vs Recaudación Ejecutada Real a lo largo de los {(modalDetail.data.meses_etiquetas || []).length} meses registrados en el Data Warehouse.
            </p>
            <div className="cmi-pred-table-scroll cmi-pred-table-scroll-lg">
              <table className="cmi-pred-table">
                <thead>
                  <tr>
                    <th scope="col">Mes</th>
                    <th scope="col">Meta Catálogo (Bs)</th>
                    <th scope="col">Recaudado Real (Bs)</th>
                    <th scope="col">Variación (Bs)</th>
                    <th scope="col">Cumplimiento</th>
                  </tr>
                </thead>
                <tbody>
                  {(modalDetail.data.meses_etiquetas || []).map((m, idx) => {
                    const meta = modalDetail.data.meta_catalogo_bs?.[idx] || 0;
                    const ejec = modalDetail.data.ejecutado_real_bs?.[idx] || 0;
                    const diff = ejec - meta;
                    const pct = meta > 0 ? ((ejec / meta) * 100).toFixed(1) : '—';
                    return (
                      <tr key={idx}>
                        <td className="cmi-bold">{m}</td>
                        <td className="cmi-mono">Bs. {meta.toLocaleString()}</td>
                        <td className="cmi-mono cmi-bold">Bs. {ejec.toLocaleString()}</td>
                        <td className={`cmi-mono ${diff >= 0 ? 'cmi-text-ok' : 'cmi-text-bad'}`}>
                          {diff >= 0 ? `+Bs. ${diff.toLocaleString()}` : `-Bs. ${Math.abs(diff).toLocaleString()}`}
                        </td>
                        <td className={`cmi-bold ${Number(pct) >= 95 ? 'cmi-text-ok' : (Number(pct) >= 85 ? 'cmi-text-gold' : 'cmi-text-bad')}`}>
                          {pct}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {modalDetail.tipo === 'caso4' && modalDetail.data && (
          <div>
            <p className="cmi-pred-modal-desc">
              OLS anual — solo descriptiva. Trayectoria plurianual de ingresos institucionales frente a la meta anual registrada en el Data Warehouse.
            </p>
            <div className="cmi-pred-justif cmi-pred-summary-row">
              <div>
                <span className="cmi-eyebrow">Meta Institucional</span>
                <div className="cmi-bold">Bs. {fmtBs(modalDetail.data.meta_anual_institucional_bs)}</div>
              </div>
              <div>
                <span className="cmi-eyebrow">Recaudado Acumulado {modalDetail.data.gestion_actual}</span>
                <div className="cmi-bold cmi-text-gold">
                  Bs. {fmtBs(modalDetail.data.recaudado_acumulado_bs)} ({modalDetail.data.porcentaje_avance_meta ?? '—'}%)
                </div>
              </div>
              <div>
                <span className="cmi-eyebrow">Pendiente OLS Anual</span>
                <div className="cmi-bold cmi-text-ok">Bs. {fmtBs(modalDetail.data.pendiente_anual_bs)}/año</div>
              </div>
              <div>
                <span className="cmi-eyebrow">CAGR Histórica</span>
                <div className="cmi-bold">+{modalDetail.data.cagr_historico_pct}%</div>
              </div>
            </div>
            <div className="cmi-pred-table-scroll">
              <table className="cmi-pred-table">
                <thead>
                  <tr>
                    <th scope="col">Año</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Monto (Bs)</th>
                    <th scope="col">Crecimiento Interanual</th>
                  </tr>
                </thead>
                <tbody>
                  {(modalDetail.data.anios_historicos || []).map((yr, idx) => (
                    <tr key={idx}>
                      <td className="cmi-bold">{yr}</td>
                      <td className="cmi-muted">Histórico Real Auditado</td>
                      <td className="cmi-mono cmi-bold">Bs. {modalDetail.data.valores_historicos_bs[idx].toLocaleString()}</td>
                      <td className="cmi-mono cmi-text-ok">
                        {idx === 0 ? '-' : `+${(((modalDetail.data.valores_historicos_bs[idx] - modalDetail.data.valores_historicos_bs[idx - 1]) / modalDetail.data.valores_historicos_bs[idx - 1]) * 100).toFixed(1)}%`}
                      </td>
                    </tr>
                  ))}
                  {(modalDetail.data.proyecciones_ols || []).map((proy, idx) => (
                    <tr key={`proy-${idx}`} className="cmi-pred-row-proy">
                      <td className="cmi-bold cmi-text-gold">{proy.periodo} (Proy)</td>
                      <td className="cmi-bold cmi-text-gold">Tendencia Lineal OLS</td>
                      <td className="cmi-mono cmi-bold">Bs. {proy.monto_proyectado_bs.toLocaleString()}</td>
                      <td className="cmi-mono cmi-text-gold">Solo descriptiva</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </aside>
    </div>
  );

  return typeof document !== 'undefined' && document.body?.appendChild
    ? createPortal(drawerNode, document.body)
    : drawerNode;
}
