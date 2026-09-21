import React, { useState } from 'react';
import { BookOpen, FileCheck2, Clock, CheckCircle2, Search } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_PROGRAMAS = [
  { id: 1, codigo: 'POS-101', nombre: 'Maestría en Big Data & DataOps', tipo: 'Maestría', modulos: 12, actas: '24 / 24', ultimoCierre: '15 Sep 2026', estado: 'Consolidado' },
  { id: 2, codigo: 'POS-102', nombre: 'Maestría en Dirección y Gestión Empresarial', tipo: 'Maestría', modulos: 14, actas: '22 / 24', ultimoCierre: '14 Sep 2026', estado: 'En Asentamiento' },
  { id: 3, codigo: 'DIP-201', nombre: 'Diplomado en Inteligencia de Negocios & CMI', tipo: 'Diplomado', modulos: 6, actas: '12 / 12', ultimoCierre: '10 Sep 2026', estado: 'Consolidado' },
  { id: 4, codigo: 'DIP-202', nombre: 'Diplomado en Finanzas Corporativas Aplicadas', tipo: 'Diplomado', modulos: 6, actas: '11 / 12', ultimoCierre: '12 Sep 2026', estado: 'En Asentamiento' },
  { id: 5, codigo: 'EXP-301', nombre: 'Programa Experto en Python para Analytics', tipo: 'Experto', modulos: 4, actas: '8 / 8', ultimoCierre: '08 Sep 2026', estado: 'Consolidado' },
  { id: 6, codigo: 'CUR-401', nombre: 'Curso de Especialización en Modelado Dimensional', tipo: 'Curso', modulos: 2, actas: '4 / 4', ultimoCierre: '01 Sep 2026', estado: 'Consolidado' },
];

export default function CatalogoCurricular() {
  useKineticScroll();
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = MOCK_PROGRAMAS.filter((p) =>
    p.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.codigo.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="DIRECCIÓN ACADÉMICA"
        title="Catálogo Curricular y"
        italicWord="Actas"
        subtitle="Control y consolidación de actas de notas por programa formativo, módulo canónico y estado de cierre en PostgreSQL."
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
          label="Programas Ofertados"
          number="14"
          sublabel="Gestión académica 2026"
          badgeText="Vigentes"
          badgeType="neutral"
        />
        <KpiCard
          label="Actas Consolidadas"
          number="81"
          numberSuffix=" / 84"
          sublabel="96.4% de actas asentadas formalmente"
          badgeText="Excelente"
          badgeType="success"
        />
        <KpiCard
          label="Actas Pendientes"
          number="3"
          sublabel="En etapa de revisión por secretaría"
          badgeText="Atención"
          badgeType="warning"
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
            placeholder="Buscar por código o programa..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
      </div>

      {/* ── Tabla de Catálogo Curricular ─────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Programa Académico</th>
              <th>Nivel / Tipo</th>
              <th>Módulos</th>
              <th>Actas Consolidadas</th>
              <th>Último Cierre</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                  {item.codigo}
                </td>
                <td style={{ fontWeight: 500 }}>{item.nombre}</td>
                <td style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>{item.tipo}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{item.modulos}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{item.actas}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                  {item.ultimoCierre}
                </td>
                <td>
                  <span
                    className={
                      item.estado === 'Consolidado'
                        ? 'badge-status badge-status-completed'
                        : 'badge-status badge-status-processing'
                    }
                  >
                    {item.estado === 'Consolidado' ? <CheckCircle2 size={12} /> : <Clock size={12} />}
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
