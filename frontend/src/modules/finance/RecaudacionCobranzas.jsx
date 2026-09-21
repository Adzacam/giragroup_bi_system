import React from 'react';
import { DollarSign, TrendingUp, CreditCard, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_HISTORICO_COBROS = [
  { periodo: 'Septiembre 2026', meta: '$ 310,000 USD', real: '$ 348,290 USD', variacion: '+$ 38,290 (+12.4%)', cuotas: 812, estado: 'Superada' },
  { periodo: 'Agosto 2026', meta: '$ 295,000 USD', real: '$ 312,450 USD', variacion: '+$ 17,450 (+5.9%)', cuotas: 780, estado: 'Superada' },
  { periodo: 'Julio 2026', meta: '$ 280,000 USD', real: '$ 278,900 USD', variacion: '-$ 1,100 (-0.4%)', cuotas: 742, estado: 'En Rango' },
  { periodo: 'Junio 2026', meta: '$ 290,000 USD', real: '$ 304,120 USD', variacion: '+$ 14,120 (+4.8%)', cuotas: 795, estado: 'Superada' },
  { periodo: 'Mayo 2026', meta: '$ 275,000 USD', real: '$ 282,300 USD', variacion: '+$ 7,300 (+2.6%)', cuotas: 730, estado: 'Superada' },
];

export default function RecaudacionCobranzas() {
  useKineticScroll();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="ANÁLISIS FINANCIERO"
        title="Panel de Cobranzas y"
        italicWord="Recaudación"
        subtitle="Monitoreo de ingresos por cobranza de cuotas, dispersión por canal de pago y cumplimiento frente a metas de caja institucional."
      />

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
          label="Recaudación Neta Mensual"
          numberPrefix="$ "
          number="348,290"
          numberSuffix=" USD"
          sublabel="Cierre parcial septiembre 2026"
          badgeText="↑ 12.4% vs meta"
          badgeType="success"
        />
        <KpiCard
          label="Cuotas Cobradas"
          number="812"
          sublabel="94.2% del volumen facturado"
          badgeText="Normal"
          badgeType="neutral"
        />
        <KpiCard
          label="Ticket Promedio"
          numberPrefix="$ "
          number="1,420"
          numberSuffix=" USD"
          sublabel="Valor medio por estudiante/mes"
          badgeText="104% Meta"
          badgeType="peach"
        />
        <KpiCard
          label="Efectividad en Pasarela"
          number="97.8"
          numberSuffix="%"
          sublabel="Pagos procesados sin rechazo"
          badgeText="Excelente"
          badgeType="success"
        />
      </div>

      {/* ── Tarjetas Informativas de Canales ─────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '24px',
          marginBottom: '36px',
        }}
      >
        <div className="card-mist kinetic-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <CreditCard size={18} color="var(--color-ink-black)" />
            <h4 className="serif-heading" style={{ fontSize: '18px', margin: 0 }}>
              Distribución por Canal de Cobro
            </h4>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Transferencia Bancaria ACH:</span>
              <strong>58.4% ($ 203,400 USD)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Pasarela QR / Débito:</span>
              <strong>32.6% ($ 113,540 USD)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Caja Central / Depósito:</span>
              <strong>9.0% ($ 31,350 USD)</strong>
            </div>
          </div>
        </div>

        <div className="card-mist kinetic-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <TrendingUp size={18} color="var(--color-alert-green)" />
            <h4 className="serif-heading" style={{ fontSize: '18px', margin: 0 }}>
              Proyección de Cierre de Mes
            </h4>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            Con el 88% de las cuotas ya cobradas a mitad de ciclo, el modelo prevé un cierre estimado de:
          </p>
          <div className="serif-display" style={{ fontSize: '28px', color: 'var(--color-ink-black)', marginBottom: '4px' }}>
            $ 362,000 &plusmn; 8,500 USD
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-alert-green)', fontWeight: 500 }}>
            Superará la meta asignada por $ 52,000 USD
          </span>
        </div>
      </div>

      {/* ── Tabla Histórica de Recaudación ───────────────────── */}
      <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
        Histórico Mensual de Cobranzas
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Periodo Mensual</th>
              <th>Meta Presupuestaria</th>
              <th>Recaudación Real</th>
              <th>Variación vs Meta</th>
              <th>Cuotas Asentadas</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_HISTORICO_COBROS.map((row, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 500 }}>{row.periodo}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{row.meta}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{row.real}</td>
                <td
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13px',
                    color: row.variacion.startsWith('+') ? 'var(--color-alert-green)' : 'var(--color-alert-red)',
                  }}
                >
                  {row.variacion}
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{row.cuotas}</td>
                <td>
                  <span className="badge-status badge-status-completed">
                    <CheckCircle2 size={12} /> {row.estado}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
