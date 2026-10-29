import React, { useState, useEffect, useCallback } from 'react';
import { BookOpen, Search, RefreshCw, Layers } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { catalogApi } from '../../api/catalogApi';

export default function CatalogoCurricular() {
  useKineticScroll();
  const [searchTerm, setSearchTerm] = useState('');
  const [modulos, setModulos] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const cargarModulos = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await catalogApi.getModulos();
      if (res && res.data) {
        setModulos(res.data);
      }
    } catch (err) {
      console.error('Error al cargar catálogo modular:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarModulos();
  }, [cargarModulos]);

  const filtered = modulos.filter((p) =>
    (p.nombre_modulo || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.programa || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.pos_code || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <PageHeader
          category="DIRECCIÓN ACADÉMICA · CATÁLOGO CURRICULAR"
          title="Catálogo Curricular y"
          italicWord="Módulos"
          subtitle="Estructura curricular de posgrados, módulos de especialidad y códigos POS consolidados en PostgreSQL (dim_modulo)."
        />
        <button
          type="button"
          onClick={cargarModulos}
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
          Actualizar Catálogo
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
          label="Módulos Registrados"
          number={String(modulos.length)}
          sublabel="Total módulos en dim_modulo"
          badgeText="Vigentes"
          badgeType="neutral"
        />
        <KpiCard
          label="Sede de Gestión"
          number="GiraGroup Posgrado"
          sublabel="Sede académica central"
          badgeText="Institucional"
          badgeType="success"
        />
        <KpiCard
          label="Calidad Curricular"
          number="100%"
          sublabel="Catálogo normalizado con códigos canónicos"
          badgeText="Auditado"
          badgeType="success"
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
            placeholder="Buscar módulo, código POS o programa..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
      </div>

      {/* ── Tabla de Módulos Curriculares ─────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Código POS</th>
              <th>Módulo Curricular</th>
              <th>Programa Académico</th>
              <th>Institución</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                  No se encontraron módulos curriculares en el catálogo.
                </td>
              </tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id_modulo}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px' }}>
                    {item.pos_code || `MOD-${item.id_modulo}`}
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.nombre_modulo}</td>
                  <td style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                    {item.programa || 'Programa General'}
                  </td>
                  <td style={{ fontSize: '12.5px' }}>{item.nombre_institucion || 'GiraGroup Posgrado'}</td>
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
                      Vigente
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
