import React, { useState, useEffect } from 'react';
import Paginacion from '../../components/shared/Paginacion';
import { BookOpen, Search, RefreshCw, Layers } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { catalogApi } from '../../api/catalogApi';

const FILAS = 5;

export default function CatalogoCurricular() {
  useKineticScroll();
  const [searchTerm, setSearchTerm] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [gestion, setGestion] = useState('');
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState({ data: [], total: 0, resumen: null, gestiones: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [recarga, setRecarga] = useState(0);

  // La búsqueda espera a que el usuario termine de escribir
  useEffect(() => {
    const t = setTimeout(() => { setBusqueda(searchTerm.trim()); setPagina(1); }, 350);
    return () => clearTimeout(t);
  }, [searchTerm]);

  useEffect(() => {
    let vigente = true;
    setIsLoading(true);
    catalogApi.getModulos({ q: busqueda || undefined, gestion: gestion || undefined, pagina, por_pagina: FILAS })
      .then((res) => { if (vigente && res) setDatos({ data: res.data || [], total: res.total || 0, resumen: res.resumen, gestiones: res.gestiones || [] }); })
      .catch((err) => console.error('Error al cargar catálogo modular:', err))
      .finally(() => { if (vigente) setIsLoading(false); });
    return () => { vigente = false; };
  }, [busqueda, gestion, pagina, recarga]);

  const cargarModulos = () => setRecarga((n) => n + 1);
  const { total, resumen } = datos;
  const totalInstituciones = resumen?.instituciones ?? 0;
  const pctConCodigo = total > 0 && resumen ? Math.round((resumen.con_codigo_pos / total) * 100) : null;
  const pag = { pagina, totalPaginas: Math.max(1, Math.ceil(total / FILAS)), total, filasPorPagina: FILAS };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <PageHeader
          category="DIRECCIÓN ACADÉMICA · CATÁLOGO CURRICULAR"
          title="Catálogo Curricular y"
          italicWord="Módulos"
          subtitle="Estructura curricular de posgrados, módulos de especialidad y códigos POS del catálogo institucional."
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
          number={String(total)}
          sublabel="Total de módulos en el catálogo"
          badgeText={busqueda || gestion ? "Filtrado" : "Total"}
          badgeType="neutral"
        />
        <KpiCard
          label="Instituciones"
          number={String(totalInstituciones)}
          sublabel="Instituciones con módulos registrados"
          badgeText="Institucional"
          badgeType="success"
        />
        <KpiCard
          label="Calidad Curricular"
          number={pctConCodigo != null ? `${pctConCodigo}%` : '—'}
          sublabel="Módulos con código POS canónico"
          badgeText={pctConCodigo === 100 ? "Completo" : "Por completar"}
          badgeType={pctConCodigo === 100 ? "success" : "neutral"}
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
            aria-label="Buscar módulo, código POS o programa"
          />
        </div>
        <select
          className="form-input"
          style={{ maxWidth: '180px' }}
          value={gestion}
          onChange={(e) => { setGestion(e.target.value); setPagina(1); }}
          aria-label="Filtrar por gestión"
        >
          <option value="">Todas las gestiones</option>
          {datos.gestiones.map((g) => <option key={g} value={g}>Gestión {g}</option>)}
        </select>
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
            </tr>
          </thead>
          <tbody>
            {datos.data.length === 0 ? (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                  {isLoading ? 'Cargando módulos…' : (busqueda || gestion ? 'Ningún módulo coincide con la búsqueda o la gestión elegida.' : 'Aún no hay módulos en el catálogo.')}
                </td>
              </tr>
            ) : (
              datos.data.map((item) => (
                <tr key={item.id_modulo}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px' }}>
                    {item.pos_code || `MOD-${item.id_modulo}`}
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.nombre_modulo}</td>
                  <td style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                    {item.programa || 'Programa General'}
                  </td>
                  <td style={{ fontSize: '12.5px' }}>{item.nombre_institucion || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <Paginacion {...pag} onChange={setPagina} />
      </ResponsiveTable>
    </div>
  );
}
