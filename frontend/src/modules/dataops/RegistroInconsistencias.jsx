import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, FileText, Filter } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_INCONSISTENCIAS = [
  {
    id: 'GIRA-43-01',
    archivo: 'Acta_POS_2026_Modulo3.xlsx',
    codigoError: 'ERR_CI_NULL',
    descripcion: 'Disparador GIRA-50: 3 cédulas de identidad ausentes o con formato dudoso ("4892019 LP?").',
    severidad: 'CRITICAL',
    registros: 3,
    estado: 'En Revisión Humana',
    fecha: '15 Sep 2026, 11:42',
  },
  {
    id: 'GIRA-43-02',
    archivo: 'Acta_POS_2026_Modulo3.xlsx',
    codigoError: 'ERR_VAL_04',
    descripcion: 'Columna "FECHA_EVAL" contiene cadenas no ISO ("12 de Septiembre"). Se aplicó cast defensivo.',
    severidad: 'WARNING',
    registros: 38,
    estado: 'Normalizado Defensivo',
    fecha: '15 Sep 2026, 11:42',
  },
  {
    id: 'GIRA-43-03',
    archivo: 'Moodle_Export_Diplomado_Agosto.csv',
    codigoError: 'ERR_HOMONIMIA',
    descripcion: 'Homonimia detectada: "Adriano Daza Meneses" vs "Daza Adriano". Score RapidFuzz 88%.',
    severidad: 'WARNING',
    registros: 1,
    estado: 'Pendiente Homologación',
    fecha: '14 Sep 2026, 18:20',
  },
  {
    id: 'GIRA-43-04',
    archivo: 'Forms_Admisiones_2026_Cohorte2.xlsx',
    codigoError: 'ERR_NOTA_OUT_OF_RANGE',
    descripcion: 'Registro con calificación = 105.0. Acotado por validador a 100.0 con advertencia.',
    severidad: 'INFO',
    registros: 1,
    estado: 'Corregido Automático',
    fecha: '12 Sep 2026, 09:15',
  },
];

export default function RegistroInconsistencias() {
  useKineticScroll();
  const [filter, setFilter] = useState('ALL');

  const filtered = filter === 'ALL'
    ? MOCK_INCONSISTENCIAS
    : MOCK_INCONSISTENCIAS.filter((item) => item.severidad === filter);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="FASE 5: GOBERNANZA &amp; AUDITORÍA"
        title="Registro de Inconsistencias"
        italicWord="GIRA-43"
        subtitle="Bitácora histórica de excepciones de validación estructural, discrepancias cross-source y disparadores GIRA-50 derivados a secretaría académica."
      />

      {/* ── KPI Summary ──────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Total Excepciones"
          number="43"
          sublabel="Lotes de septiembre 2026"
          badgeText="Bitácora"
          badgeType="neutral"
        />
        <KpiCard
          label="Críticas (GIRA-50)"
          number="3"
          sublabel="Cédula ausente o ambigua"
          badgeText="Atención Prioritaria"
          badgeType="danger"
        />
        <KpiCard
          label="Normalizadas Auto"
          number="38"
          sublabel="Cast de fechas y trim de espacios"
          badgeText="95.8% Pipeline"
          badgeType="success"
        />
      </div>

      {/* ── Filter Buttons ───────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', alignItems: 'center' }}>
        <Filter size={15} color="var(--color-slate-gray)" />
        <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginRight: '6px' }}>Filtrar severidad:</span>
        <button
          onClick={() => setFilter('ALL')}
          className={filter === 'ALL' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Todas
        </button>
        <button
          onClick={() => setFilter('CRITICAL')}
          className={filter === 'CRITICAL' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Críticas
        </button>
        <button
          onClick={() => setFilter('WARNING')}
          className={filter === 'WARNING' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Advertencias
        </button>
      </div>

      {/* ── Tabla de Inconsistencias ─────────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Ticket ID</th>
              <th>Archivo Origen</th>
              <th>Código Error</th>
              <th>Descripción Técnica</th>
              <th>Filas</th>
              <th>Severidad</th>
              <th>Estado</th>
              <th>Fecha Registro</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className={item.severidad === 'CRITICAL' ? 'row-critical-alert' : ''}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12.5px' }}>
                  {item.id}
                </td>
                <td style={{ fontSize: '13px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <FileText size={14} color="var(--color-slate-gray)" />
                    <span>{item.archivo}</span>
                  </div>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-sienna-brown)' }}>
                  {item.codigoError}
                </td>
                <td style={{ fontSize: '13px', maxWidth: '340px' }}>{item.descripcion}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{item.registros}</td>
                <td>
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
                      backgroundColor: item.severidad === 'CRITICAL' ? '#fee2e2' : item.severidad === 'WARNING' ? '#fef3c7' : '#e0f2fe',
                      color: item.severidad === 'CRITICAL' ? 'var(--color-alert-red)' : item.severidad === 'WARNING' ? 'var(--color-alert-amber)' : '#0369a1',
                    }}
                  >
                    {item.severidad}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: '12.5px', color: 'var(--color-ink-black)', fontWeight: 500 }}>
                    {item.estado}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>
                  {item.fecha}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
