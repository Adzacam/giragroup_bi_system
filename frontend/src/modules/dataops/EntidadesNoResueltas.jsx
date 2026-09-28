import React, { useState } from 'react';
import { GitMerge, CheckCircle2, Link2, Sparkles, Filter } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { sileoToast } from '../../services/sileoToast';

const INITIAL_ENTITIES = [
  {
    id: 'ENT-01',
    cadena: '"Dr. Carlos Alberto Gomez M."',
    entidadSugerida: 'Dr. Carlos A. Gómez Murillo',
    codigo: 'DOC-109',
    tipo: 'Docente',
    score: 88,
    estado: 'pending' // 'pending' | 'linked'
  },
  {
    id: 'ENT-02',
    cadena: '"Gest. Datos / Mod 3"',
    entidadSugerida: 'MOD-302: Gestión de Datos',
    codigo: 'POS-MOD-302',
    tipo: 'Módulo Curricular',
    score: 92,
    estado: 'linked'
  },
  {
    id: 'ENT-03',
    cadena: '"Adriano Daza Meneses"',
    entidadSugerida: 'Daza Meneses, Adriano',
    codigo: 'EST-4892019',
    tipo: 'Estudiante',
    score: 95,
    estado: 'linked'
  },
  {
    id: 'ENT-04',
    cadena: '"Diplomado Big Data & IA 2026"',
    entidadSugerida: 'DIP-BD-IA: Diplomado en Big Data e Inteligencia Artificial',
    codigo: 'PROG-401',
    tipo: 'Programa Académico',
    score: 91,
    estado: 'pending'
  }
];

export default function EntidadesNoResueltas() {
  const [entities, setEntities] = useState(INITIAL_ENTITIES);
  const [filter, setFilter] = useState('ALL');

  const handleLink = (id, name, suggested) => {
    setEntities(prev => prev.map(e => e.id === id ? { ...e, estado: 'linked' } : e));
    sileoToast.success({
      title: 'Entidad Vinculada al Catálogo',
      description: `"${name}" fue vinculada exitosamente a "${suggested}".`
    });
  };

  const handleUnlink = (id, name) => {
    setEntities(prev => prev.map(e => e.id === id ? { ...e, estado: 'pending' } : e));
    sileoToast.info({
      title: 'Vinculación Revertida',
      description: `La entidad "${name}" volvió al estado pendiente.`
    });
  };

  const total = entities.length;
  const linkedCount = entities.filter(e => e.estado === 'linked').length;
  const pendingCount = entities.filter(e => e.estado === 'pending').length;
  const avgScore = (entities.reduce((acc, e) => acc + e.score, 0) / total).toFixed(1);

  const filtered = filter === 'ALL' 
    ? entities 
    : filter === 'PENDING' 
    ? entities.filter(e => e.estado === 'pending')
    : entities.filter(e => e.estado === 'linked');

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <PageHeader
        category="Gobernanza &amp; Catálogos Canónicos"
        title="Entidades No Resueltas (RapidFuzz)"
        subtitle="Sugerencias inteligentes de homologación hacia catálogos maestros 3NF para entidades docentes, módulos y estudiantes con discrepancias de sintaxis."
      />

      {/* ── KPI Summary Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Total Entidades Analizadas
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>
            {total} casos
          </div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Vinculadas al Catálogo
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-green)' }}>
            {linkedCount} entidades
          </div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)', border: pendingCount > 0 ? '1px solid rgba(217, 155, 38, 0.4)' : undefined }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: pendingCount > 0 ? 'var(--color-gira-gold)' : 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Pendientes de Conciliación
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: pendingCount > 0 ? 'var(--color-gira-gold)' : 'var(--color-ink-black)' }}>
            {pendingCount} casos
          </div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Precisión Promedio RapidFuzz
          </h3>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)' }}>
            {avgScore}%
          </div>
        </div>
      </div>

      {/* ── Filter Buttons ── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', alignItems: 'center' }}>
        <Filter size={15} color="var(--color-slate-gray)" />
        <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginRight: '6px' }}>Filtrar estado:</span>
        <button
          onClick={() => setFilter('ALL')}
          className={filter === 'ALL' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Todas ({total})
        </button>
        <button
          onClick={() => setFilter('PENDING')}
          className={filter === 'PENDING' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Pendientes ({pendingCount})
        </button>
        <button
          onClick={() => setFilter('LINKED')}
          className={filter === 'LINKED' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '5px 14px', fontSize: '12px' }}
        >
          Vinculadas ({linkedCount})
        </button>
      </div>

      {/* ── Table ── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cadena Detectada en Fuentes</th>
              <th>Tipo de Entidad</th>
              <th>Entidad Canónica Sugerida (Catálogo 3NF)</th>
              <th>Score Match</th>
              <th>Estado</th>
              <th>Acción de Gobernanza</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                  {item.cadena}
                </td>
                <td style={{ fontSize: '12.5px', fontWeight: 500 }}>
                  <span style={{ 
                    padding: '3px 8px', 
                    borderRadius: '6px', 
                    fontSize: '11px', 
                    backgroundColor: 'var(--color-mist-gray)',
                    color: 'var(--color-ink-black)',
                    fontFamily: 'var(--font-sohne)'
                  }}>
                    {item.tipo}
                  </span>
                </td>
                <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                  {item.entidadSugerida} <span style={{ color: 'var(--color-slate-gray)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>({item.codigo})</span>
                </td>
                <td>
                  <span className={item.score >= 90 ? "badge-status badge-status-completed" : "badge-status badge-status-processing"}>
                    {item.score}%
                  </span>
                </td>
                <td>
                  {item.estado === 'linked' ? (
                    <span style={{ color: 'var(--color-alert-green)', fontSize: '12px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={13} /> Vinculado
                    </span>
                  ) : (
                    <span style={{ color: 'var(--color-gira-gold)', fontSize: '12px', fontWeight: 600 }}>
                      Pendiente
                    </span>
                  )}
                </td>
                <td>
                  {item.estado === 'linked' ? (
                    <button 
                      type="button" 
                      className="btn-pill-ghost" 
                      onClick={() => handleUnlink(item.id, item.cadena)}
                      style={{ padding: '5px 14px', fontSize: '12px' }}
                    >
                      Desvincular
                    </button>
                  ) : (
                    <button 
                      type="button" 
                      className="btn-pill-dark" 
                      onClick={() => handleLink(item.id, item.cadena, item.entidadSugerida)}
                      style={{ padding: '6px 16px', fontSize: '12.5px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Link2 size={13} /> Vincular
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
