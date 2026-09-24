import React from 'react';
import { Target, TrendingUp, CheckCircle2, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_METAS = [
  { id: 1, codigo: 'POS-101', programa: 'Maestría en Big Data & DataOps', meta: 'Bs. 500,000', ejecutado: 'Bs. 470,000', porcentaje: 94.0, estado: 'En Meta' },
  { id: 2, codigo: 'POS-102', programa: 'Maestría en Dirección y Gestión', meta: 'Bs. 480,000', ejecutado: 'Bs. 512,000', porcentaje: 106.7, estado: 'Superada' },
  { id: 3, codigo: 'DIP-201', programa: 'Diplomado en BI & CMI Estratégico', meta: 'Bs. 320,000', ejecutado: 'Bs. 345,000', porcentaje: 107.8, estado: 'Superada' },
  { id: 4, codigo: 'DIP-202', programa: 'Diplomado en Finanzas Corporativas', meta: 'Bs. 280,000', ejecutado: 'Bs. 240,000', porcentaje: 85.7, estado: 'En Riesgo' },
  { id: 5, codigo: 'EXP-301', programa: 'Programa Experto en Python Analytics', meta: 'Bs. 190,000', ejecutado: 'Bs. 188,000', porcentaje: 98.9, estado: 'En Meta' },
  { id: 6, codigo: 'CUR-401', programa: 'Curso Modelado Dimensional Kimball', meta: 'Bs. 95,000', ejecutado: 'Bs. 102,000', porcentaje: 107.4, estado: 'Superada' },
];

export default function MetasGestion() {
  useKineticScroll();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="ANÁLISIS FINANCIERO"
        title="Metas de Gestión vs."
        italicWord="Ejecutado"
        subtitle="Evaluación presupuestaria por programa académico, control de dispersión de ingresos y cálculo de desvíos frente a metas institucionales."
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
          label="Meta Global Gestión 2026"
          numberPrefix="Bs. "
          number="3,800,000"
          numberSuffix=""
          sublabel="Techo presupuestario institucional"
          badgeText="Presupuesto"
          badgeType="neutral"
        />
        <KpiCard
          label="Recaudación Acumulada"
          numberPrefix="Bs. "
          number="3,480,000"
          numberSuffix=""
          sublabel="91.6% de la meta anual a septiembre"
          badgeText="En Trayectoria"
          badgeType="success"
        />
        <KpiCard
          label="Desviación Favorable"
          numberPrefix="+Bs. "
          number="140,000"
          numberSuffix=""
          sublabel="Superávit sobre proyección lineal"
          badgeText="Positivo"
          badgeType="peach"
        />
        <KpiCard
          label="Cumplimiento de Programas"
          number="11"
          numberSuffix=" / 14"
          sublabel="78.5% de la oferta en meta o superada"
          badgeText="Óptimo"
          badgeType="success"
        />
      </div>

      {/* ── Tabla de Metas por Programa ──────────────────────── */}
      <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
        Desglose de Ejecución por Programa Formativo
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Programa Académico</th>
              <th>Meta Asignada</th>
              <th>Recaudado Real</th>
              <th style={{ minWidth: '180px' }}>Cumplimiento (%)</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_METAS.map((item) => (
              <tr key={item.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                  {item.codigo}
                </td>
                <td style={{ fontWeight: 500 }}>{item.programa}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{item.meta}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{item.ejecutado}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        flex: 1,
                        height: '7px',
                        borderRadius: '9999px',
                        backgroundColor: 'var(--color-mist-gray)',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.min(item.porcentaje, 100)}%`,
                          height: '100%',
                          backgroundColor:
                            item.porcentaje >= 100
                              ? 'var(--color-alert-green)'
                              : item.porcentaje >= 90
                              ? 'var(--color-ink-black)'
                              : 'var(--color-alert-amber)',
                          borderRadius: '9999px',
                        }}
                      />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600 }}>
                      {item.porcentaje.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td>
                  <span
                    className={
                      item.estado === 'Superada' || item.estado === 'En Meta'
                        ? 'badge-status badge-status-completed'
                        : 'badge-status badge-status-processing'
                    }
                  >
                    {item.estado}
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
