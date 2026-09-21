import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Search, ShieldAlert, PhoneCall } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_MORA = [
  { id: 1, ci: '4892019 LP', estudiante: 'Daza Meneses Adriano', programa: 'POS-101: Maestría en Big Data', cuotas: 2, monto: '$ 1,200 USD', dias: 45, riesgo: 'Moderado', gestion: 'Notificado WhatsApp' },
  { id: 2, ci: '3948102 SC', estudiante: 'Flores Choque Maribel', programa: 'DIP-201: Diplomado en BI & CMI', cuotas: 3, monto: '$ 1,850 USD', dias: 72, riesgo: 'Alto', gestion: 'Carta Notarial' },
  { id: 3, ci: '5829104 CB', estudiante: 'Vargas Alarcón Javier', programa: 'POS-102: Maestría en Dirección', cuotas: 1, monto: '$ 650 USD', dias: 18, riesgo: 'Bajo', gestion: 'Recordatorio Correo' },
  { id: 4, ci: '7482910 LP', estudiante: 'Mamani Quispe Gonzalo', programa: 'EXP-301: Experto en Python Analytics', cuotas: 1, monto: '$ 450 USD', dias: 24, riesgo: 'Bajo', gestion: 'Compromiso 20 Sep' },
  { id: 5, ci: '6192830 SC', estudiante: 'Salazar Cortez Gabriela', programa: 'POS-101: Maestría en Big Data', cuotas: 4, monto: '$ 2,400 USD', dias: 94, riesgo: 'Alto', gestion: 'En Bloqueo Plataforma' },
];

export default function CarteraMora() {
  useKineticScroll();
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = MOCK_MORA.filter((m) =>
    m.estudiante.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.ci.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.programa.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="ANÁLISIS FINANCIERO"
        title="Gestión de Cartera, Mora y"
        italicWord="Riesgo"
        subtitle="Control de cuentas por cobrar vencidas, clasificación de riesgo crediticio y gestión de cobranzas preventivas."
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
          label="Estudiantes en Mora"
          number="42"
          numberSuffix=" alumnos"
          sublabel="3.3% del total de inscritos activos"
          badgeText="Alerta Cartera"
          badgeType="danger"
        />
        <KpiCard
          label="Saldo Exigible Vencido"
          numberPrefix="$ "
          number="58,400"
          numberSuffix=" USD"
          sublabel="Total cuotas acumuladas vencidas"
          badgeText="A recuperar"
          badgeType="warning"
        />
        <KpiCard
          label="Cartera Vigente al Día"
          numberPrefix="$ "
          number="1,640,000"
          numberSuffix=" USD"
          sublabel="96.7% de solvencia institucional"
          badgeText="Sana"
          badgeType="success"
        />
        <KpiCard
          label="Cobranza Recuperada"
          numberPrefix="$ "
          number="18,200"
          numberSuffix=" USD"
          sublabel="Recaudado en primeros 15 días"
          badgeText="En Meta"
          badgeType="peach"
        />
      </div>

      {/* ── Buscador ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center' }}>
        <div style={{ position: 'relative', maxWidth: '380px', width: '100%' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--color-slate-gray)' }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por estudiante, CI o programa..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
      </div>

      {/* ── Tabla de Cartera y Mora ──────────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cédula (CI)</th>
              <th>Estudiante</th>
              <th>Programa Académico</th>
              <th>Cuotas</th>
              <th>Saldo Vencido</th>
              <th>Días Mora</th>
              <th>Nivel Riesgo</th>
              <th>Última Gestión</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className={item.riesgo === 'Alto' ? 'row-critical-alert' : ''}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                  {item.ci}
                </td>
                <td style={{ fontWeight: 500 }}>{item.estudiante}</td>
                <td style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>{item.programa}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{item.cuotas}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>{item.monto}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  {item.dias} días
                </td>
                <td>
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 600,
                      backgroundColor:
                        item.riesgo === 'Alto'
                          ? '#fee2e2'
                          : item.riesgo === 'Moderado'
                          ? '#fef3c7'
                          : '#e0f2fe',
                      color:
                        item.riesgo === 'Alto'
                          ? 'var(--color-alert-red)'
                          : item.riesgo === 'Moderado'
                          ? 'var(--color-alert-amber)'
                          : '#0369a1',
                    }}
                  >
                    {item.riesgo}
                  </span>
                </td>
                <td style={{ fontSize: '12.5px' }}>{item.gestion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
