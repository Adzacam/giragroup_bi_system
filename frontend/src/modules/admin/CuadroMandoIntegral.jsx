import React from 'react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { ShieldCheck, TrendingUp, DollarSign, Award, Users, AlertCircle } from 'lucide-react';

export default function CuadroMandoIntegral() {
  useKineticScroll();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="ADMINISTRACIÓN TOTAL"
        title="Cuadro de Mando Integral"
        italicWord="Ejecutivo"
        subtitle="Consolidado institucional del Balanced Scorecard alineado a metas financieras, retención curricular y calidad de datos DataOps."
      />

      {/* ── 3 Pilares Principales (KPI Cards) ────────────────────────── */}
      <div className="cmi-kpi-grid">
        <KpiCard
          label="1. FINANCIERA"
          numberPrefix="Bs. "
          number="1,420"
          numberSuffix=""
          sublabel="Ticket promedio (104% meta)"
          badgeText="Superávit"
          badgeType="success"
          className="kinetic-left in-view"
        />

        <KpiCard
          label="2. ACADÉMICA"
          number="94.8"
          numberSuffix="% Retención"
          sublabel="24 estudiantes en alerta"
          badgeText="Atención"
          badgeType="danger"
          className="kinetic-center in-view"
        />

        <KpiCard
          label="3. PROCESOS DATAOPS"
          number="98.1"
          numberSuffix="% Limpios"
          sublabel="Inferencia BETO nominal"
          badgeText="Gobernado"
          badgeType="peach"
          className="kinetic-right in-view"
        />
      </div>

      {/* ── Desglose Ejecutivo por Perspectiva ───────────────────────── */}
      <div className="cmi-perspective-grid">
        {/* Perspectiva Clientes & Alumnos */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Users size={18} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Perspectiva Estudiantil &amp; Mercado
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '16px' }}>
            Seguimiento de cohortes activas en programas de Postgrado y Educación Continua.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Matrícula Vigente</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>1,248 alumnos</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>NPS Satisfacción Cátedra</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>4.72 / 5.0</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Riesgo Deserción (Notas ≤ 70)</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-alert-red)' }}>1.9% cohorte</span>
          </div>
        </div>

        {/* Perspectiva Eficiencia & Gobernanza */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <ShieldCheck size={18} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Gobernanza de Datos &amp; Compliance
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '16px' }}>
            Auditoría automatizada de fuentes externas, concordancia difusa y preservación dimensional.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Regla de Integridad de CI (Requerido)</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>0 bypass activo</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Latencia Media Inferencia NLP</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>1.42s / lote</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Seguridad RBAC &amp; PoLP</span>
            <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>Vigente (RLS Activo)</span>
          </div>
        </div>
      </div>

      {/* ── Tabla de Resumen Institucional ───────────────────────────── */}
      <div style={{ marginTop: '40px' }}>
        <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
          Consolidado de Metas por Dirección
        </h3>
        <ResponsiveTable>
          <table className="steep-table">
            <thead>
              <tr>
                <th>Dirección</th>
                <th>Objetivo Estratégico</th>
                <th>Indicador Clave</th>
                <th>Meta 2026</th>
                <th>Real Actual</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Financiera</strong></td>
                <td>Sostenibilidad y Flujo de Caja</td>
                <td>Recaudación Neta Mensual</td>
                <td>Bs. 310,000</td>
                <td>Bs. 348,290</td>
                <td><span className="badge-status badge-status-completed">112% Superada</span></td>
              </tr>
              <tr>
                <td><strong>Académica</strong></td>
                <td>Retención Estudiantil Temprana</td>
                <td>Alumnos con Nota &gt; 70</td>
                <td>&gt; 92.0%</td>
                <td>94.8%</td>
                <td><span className="badge-status badge-status-completed">Conforme</span></td>
              </tr>
              <tr>
                <td><strong>DataOps</strong></td>
                <td>Normalización Libre de Ambigüedad</td>
                <td>Tasa Limpieza Automática</td>
                <td>&gt; 90.0%</td>
                <td>95.8%</td>
                <td><span className="badge-status badge-status-completed">Conforme</span></td>
              </tr>
              <tr>
                <td><strong>Auditoría</strong></td>
                <td>Resolución Homonimia Docente</td>
                <td>Entidades Vinculadas Canónicamente</td>
                <td>100%</td>
                <td>98.4%</td>
                <td><span className="badge-status badge-status-processing">En Resolución</span></td>
              </tr>
            </tbody>
          </table>
        </ResponsiveTable>
      </div>
    </div>
  );
}
