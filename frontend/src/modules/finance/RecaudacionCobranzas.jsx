import React from 'react';
import usePaginacion from '../../hooks/usePaginacion';
import Paginacion from '../../components/shared/Paginacion';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { DollarSign, TrendingUp, CreditCard, RefreshCw } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { kpiApi } from '../../api/kpiApi';
import client from '../../api/client';

export default function RecaudacionCobranzas() {
  useKineticScroll();

  const {
    data: datosCobro = {
      recaudacionNetaBs: null,
      cumplimientoPct: null,
      totalDeudaMoraBs: 0,
      historicoMeses: [],
    },
    isLoading,
    isFetching,
    refetch: cargarCobranzas,
  } = useQuery({
    queryKey: ['finance', 'recaudacion-cobranzas'],
    queryFn: async () => {
      const [kpiRes, macroRes] = await Promise.allSettled([
        kpiApi.getKpisFinanciero(),
        client.get('/api/v1/forecast/analitica-macro'),
      ]);

      const deudaBs = kpiRes.status === 'fulfilled' ? Number(kpiRes.value?.monto_total_deuda_bs ?? 0) : 0;
      const macro = macroRes.status === 'fulfilled' ? macroRes.value?.data : null;
      const c3 = macro?.caso3_metas_mensuales;
      const c4 = macro?.caso4_metas_anuales;

      // Meses reales (meta vs ejecutado de fact_rentabilidad) + proyección Holt-Winters
      const reales = (c3?.meses_etiquetas || []).map((periodo, i) => ({
        periodo,
        meta_bs: c3.meta_catalogo_bs?.[i] ?? null,
        ejecutado_bs: c3.ejecutado_real_bs?.[i] ?? null,
      }));
      const proyectados = (c3?.proyecciones_hw || []).map((p) => ({
        periodo: `${p.periodo} (HW)`,
        proyeccion_bs: p.monto_proyectado_bs,
        ic_lower: p.ic_lower,
        ic_upper: p.ic_upper,
      }));

      return {
        recaudacionNetaBs: c4?.recaudado_acumulado_bs ?? null,
        totalDeudaMoraBs: deudaBs,
        cumplimientoPct: c4?.porcentaje_avance_meta ?? null,
        historicoMeses: [...reales, ...proyectados],
        motivoSinDatos: macro?.sin_datos?.caso3 || null,
      };
    },
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });
  const pagHist = usePaginacion(datosCobro.historicoMeses);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <PageHeader
          category="ANÁLISIS FINANCIERO · DATA WAREHOUSE"
          title="Panel de Cobranzas y"
          italicWord="Recaudación"
          subtitle="Monitoreo de ingresos devengados vs cobrados, cuotas de posgrado consolidadas y cumplimiento frente a metas de caja institucional."
        />
        <button
          type="button"
          onClick={cargarCobranzas}
          disabled={isLoading}
          style={{
            marginTop: '18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            fontSize: '12.5px',
            fontWeight: 700,
            borderRadius: '10px',
            border: '1px solid var(--color-border)',
            background: 'var(--color-paper-white)',
            color: 'var(--color-ink-black)',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Actualizar Cobranzas
        </button>
      </div>

      {/* ── KPIs ─────────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Recaudación Neta Registrada"
          numberPrefix="Bs. "
          number={datosCobro.recaudacionNetaBs != null ? Number(datosCobro.recaudacionNetaBs).toLocaleString('es-BO') : '—'}
          numberSuffix=""
          sublabel="Ejecutado acumulado de la gestión en DW"
          badgeText={datosCobro.recaudacionNetaBs != null ? 'Verificado' : 'Sin datos'}
          badgeType={datosCobro.recaudacionNetaBs != null ? 'success' : 'neutral'}
        />
        <KpiCard
          label="Cartera Vencida Exigible"
          numberPrefix="Bs. "
          number={Number(datosCobro.totalDeudaMoraBs || 0).toLocaleString()}
          numberSuffix=""
          sublabel="Saldo pendiente en fact_situacion_financiera"
          badgeText={datosCobro.totalDeudaMoraBs > 0 ? "Mora Activa" : "Sana"}
          badgeType={datosCobro.totalDeudaMoraBs > 0 ? "warning" : "success"}
        />
        <KpiCard
          label="Cumplimiento Presupuestario"
          number={datosCobro.cumplimientoPct != null ? String(datosCobro.cumplimientoPct) : '—'}
          numberSuffix={datosCobro.cumplimientoPct != null ? '%' : ''}
          sublabel="Ejecutado vs meta de la gestión (fact_rentabilidad)"
          badgeText={datosCobro.cumplimientoPct == null ? 'Sin datos' : (datosCobro.cumplimientoPct >= 90 ? 'En Rango' : 'Bajo Meta')}
          badgeType={datosCobro.cumplimientoPct == null ? 'neutral' : (datosCobro.cumplimientoPct >= 90 ? 'success' : 'warning')}
        />
      </div>

      {/* ── Tabla de Monitoreo de Cuotas y Metas Mensuales ──────── */}
      <h3 className="serif-heading" style={{ fontSize: '20px', marginBottom: '16px' }}>
        Comportamiento Mensual de Ingresos y Metas Institucionales
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Periodo</th>
              <th>Meta Mensual</th>
              <th>Ejecutado / Proyección HW</th>
              <th>IC 95% Inferior</th>
              <th>IC 95% Superior</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {datosCobro.historicoMeses.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                  {isLoading ? 'Cargando serie analítica de cobranzas...' : (datosCobro.motivoSinDatos || 'Sin metas ni ejecución financiera en el Data Warehouse.')}
                </td>
              </tr>
            ) : (
              pagHist.visibles.map((m, idx) => (
                <tr key={idx}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                    {m.periodo}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                    {m.meta_bs != null ? `Bs. ${Number(m.meta_bs).toLocaleString('es-BO')}` : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: '#D99B26' }}>
                    {(m.ejecutado_bs ?? m.proyeccion_bs) != null ? `Bs. ${Number(m.ejecutado_bs ?? m.proyeccion_bs).toLocaleString('es-BO')}` : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                    {m.ic_lower != null ? `Bs. ${Number(m.ic_lower).toLocaleString('es-BO')}` : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                    {m.ic_upper != null ? `Bs. ${Number(m.ic_upper).toLocaleString('es-BO')}` : '—'}
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '3px 10px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: 'rgba(27, 135, 84, 0.12)',
                        color: 'var(--color-alert-green)',
                        border: '1px solid rgba(27, 135, 84, 0.3)',
                      }}
                    >
                      {m.proyeccion_bs != null ? 'Proyección' : (m.meta_bs && m.ejecutado_bs != null ? (m.ejecutado_bs >= m.meta_bs ? 'En Meta' : 'Bajo Meta') : '—')}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <Paginacion {...pagHist} onChange={pagHist.setPagina} />
      </ResponsiveTable>
    </div>
  );
}
