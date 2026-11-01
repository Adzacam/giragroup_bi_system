import React, { useState, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Database, Plus, Search, CheckCircle, RefreshCw, X, Trash2, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { useTheme } from '../../context/ThemeContext';
import { catalogApi } from '../../api/catalogApi';

export default function CatalogosMaestros() {
  useKineticScroll();
  const { isDark } = useTheme();

  const [activeTab, setActiveTab] = useState('modulos'); // 'modulos' | 'docentes' | 'categorias'
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [newEntry, setNewEntry] = useState({ codigo: '', nombre: '', extra: '', institucion: 'GiraGroup Posgrado' });

  const {
    data: catalogData,
    isLoading: loading,
    error: queryError,
    refetch: loadData,
  } = useQuery({
    queryKey: ['admin', 'catalogos-maestros'],
    queryFn: async () => {
      const [modRes, docRes, finRes] = await Promise.all([
        catalogApi.getModulos().catch(() => ({ data: [] })),
        catalogApi.getDocentes().catch(() => ({ data: [] })),
        catalogApi.getFinancialConcepts().catch(() => []),
      ]);

      return {
        modulos: Array.isArray(modRes?.data) ? modRes.data : Array.isArray(modRes) ? modRes : [],
        docentes: Array.isArray(docRes?.data) ? docRes.data : Array.isArray(docRes) ? docRes : [],
        conceptos: Array.isArray(finRes) ? finRes : Array.isArray(finRes?.data) ? finRes.data : [],
      };
    },
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });

  const error = queryError ? 'No se pudieron recuperar los catálogos dimensionales desde PostgreSQL.' : null;
  const modulosList = catalogData?.modulos || [];
  const docentesList = catalogData?.docentes || [];
  const conceptosList = catalogData?.conceptos || [];

  const currentList = useMemo(() => {
    const q = searchTerm.toLowerCase();
    if (activeTab === 'modulos') {
      return modulosList.filter(item =>
        (item.nombre_modulo || '').toLowerCase().includes(q) ||
        (item.pos_code || '').toLowerCase().includes(q) ||
        (item.programa || '').toLowerCase().includes(q)
      );
    }
    if (activeTab === 'docentes') {
      return docentesList.filter(item =>
        (item.nombre_completo || '').toLowerCase().includes(q) ||
        (item.area_especialidad || '').toLowerCase().includes(q)
      );
    }
    if (activeTab === 'categorias') {
      return conceptosList.filter(item =>
        (item.nombre_canonico || '').toLowerCase().includes(q) ||
        (item.codigo_canonico || '').toLowerCase().includes(q) ||
        (item.descripcion || '').toLowerCase().includes(q)
      );
    }
    return [];
  }, [activeTab, searchTerm, modulosList, docentesList, conceptosList]);


  const handleAdd = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (activeTab === 'modulos') {
        await catalogApi.createModulo({
          nombre_modulo: newEntry.nombre,
          pos_code: newEntry.codigo || 'MOD-GEN',
          nombre_institucion: newEntry.institucion || 'GiraGroup Posgrado',
          programa: newEntry.extra || 'Programa General'
        });
      } else if (activeTab === 'docentes') {
        await catalogApi.createDocente({
          nombre_completo: newEntry.nombre,
          area_especialidad: newEntry.extra || 'General'
        });
      }
      setIsModalOpen(false);
      setNewEntry({ codigo: '', nombre: '', extra: '', institucion: 'GiraGroup Posgrado' });
      await loadData();
    } catch (err) {
      console.error('Error al crear registro de catálogo:', err);
      alert('Error al registrar en PostgreSQL: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="DIMENSIONES CANÓNICAS POSTGRESQL"
        title="Catálogos Maestros"
        italicWord="Dimensionales"
        subtitle="Mantenimiento y sincronización de tablas dimensionales canónicas (dim_modulo, dim_docente, cat_conceptos_financieros) que alimentan el esquema constelación."
        action={
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => loadData()}
              className="btn-pill-ghost"
              type="button"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
              title="Recargar desde base de datos"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refrescar
            </button>
            {activeTab !== 'categorias' && (
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-pill-dark"
                type="button"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                <Plus size={16} /> Añadir {activeTab === 'modulos' ? 'Módulo' : 'Docente'}
              </button>
            )}
          </div>
        }
      />

      {/* ── Tabs Selector ────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '24px',
          flexWrap: 'wrap',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: '12px',
        }}
      >
        <button
          onClick={() => { setActiveTab('modulos'); setSearchTerm(''); }}
          className={activeTab === 'modulos' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '8px 18px', fontSize: '13.5px' }}
        >
          Módulos y Programas ({modulosList.length})
        </button>
        <button
          onClick={() => { setActiveTab('docentes'); setSearchTerm(''); }}
          className={activeTab === 'docentes' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '8px 18px', fontSize: '13.5px' }}
        >
          Plantel Docente ({docentesList.length})
        </button>
        <button
          onClick={() => { setActiveTab('categorias'); setSearchTerm(''); }}
          className={activeTab === 'categorias' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '8px 18px', fontSize: '13.5px' }}
        >
          Conceptos Financieros ({conceptosList.length})
        </button>
      </div>

      {/* ── Search & Filter bar ──────────────────────────────── */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center' }}>
        <div style={{ position: 'relative', maxWidth: '380px', width: '100%' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--color-slate-gray)' }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por código, nombre o especialidad..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
          Total registros sincronizados: <strong>{currentList.length}</strong>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }} role="status" aria-live="polite">
          <div className="skeleton-shimmer" style={{ height: '52px', width: '100%' }} />
          <div className="skeleton-shimmer" style={{ height: '240px', width: '100%' }} />
        </div>
      ) : error ? (
        <div style={{ padding: '24px', backgroundColor: 'rgba(217, 56, 58, 0.08)', borderRadius: '12px', border: '1px solid var(--color-alert-red)', color: 'var(--color-alert-red)', marginBottom: '24px' }}>
          <AlertCircle size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
          {error}
        </div>
      ) : (
        <ResponsiveTable>
          <table className="steep-table">
            <thead>
              <tr>
                <th>Código Canónico</th>
                <th>Descripción / Nombre</th>
                {activeTab === 'modulos' && <th>Programa / Institución</th>}
                {activeTab === 'docentes' && <th>Área Especialidad</th>}
                {activeTab === 'categorias' && <th>Tipo / Categoría</th>}
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {currentList.length > 0 ? (
                currentList.map((row, idx) => {
                  const id = row.id_modulo || row.id_docente || row.id_concepto || idx;
                  const codigo = row.pos_code || `DOC-${row.id_docente}` || row.codigo_canonico || `CAT-${id}`;
                  const nombre = row.nombre_modulo || row.nombre_completo || row.nombre_canonico || 'Sin nombre';

                  return (
                    <tr key={id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                        {codigo}
                      </td>
                      <td style={{ fontWeight: 500 }}>{nombre}</td>
                      {activeTab === 'modulos' && (
                        <td>
                          <span style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                            {row.programa || row.nombre_institucion || 'GiraGroup Posgrado'}
                          </span>
                        </td>
                      )}
                      {activeTab === 'docentes' && (
                        <td>
                          <span style={{ fontSize: '12.5px', color: 'var(--color-ink-black)' }}>
                            {row.area_especialidad || 'Cátedra General'}
                          </span>
                        </td>
                      )}
                      {activeTab === 'categorias' && (
                        <td>
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontFamily: 'var(--font-mono)',
                              backgroundColor: row.tipo_movimiento === 'INGRESO' ? '#dcfce7' : '#fee2e2',
                              color: row.tipo_movimiento === 'INGRESO' ? 'var(--color-alert-green)' : 'var(--color-alert-red)',
                            }}
                          >
                            {row.tipo_movimiento} · {row.categoria_contable}
                          </span>
                        </td>
                      )}
                      <td>
                        <span className="badge-status badge-status-completed">
                          <CheckCircle size={12} /> Vigente
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-slate-gray)' }}>
                    No se encontraron registros que coincidan con la búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </ResponsiveTable>
      )}

      {/* ── Modal Alta Registro ──────────────────────────────── */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(23, 25, 28, 0.45)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            className="floating-artifact"
            style={{
              width: '100%',
              maxWidth: '480px',
              padding: '30px',
              borderRadius: 'var(--radius-cards)',
              backgroundColor: isDark ? 'var(--color-bg-card)' : 'var(--color-paper-white)',
              boxShadow: 'var(--shadow-modal)',
              animation: 'modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
                Nuevo Registro ({activeTab === 'modulos' ? 'Módulo Curricular' : 'Docente'})
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                type="button"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {activeTab === 'modulos' && (
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                    Código Canónico POS / MOD
                  </label>
                  <input
                    type="text"
                    required
                    value={newEntry.codigo}
                    onChange={(e) => setNewEntry({ ...newEntry, codigo: e.target.value })}
                    placeholder="ej. POS-105 o MOD-12"
                    className="form-input"
                  />
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  {activeTab === 'modulos' ? 'Nombre del Módulo' : 'Nombre Completo del Docente'}
                </label>
                <input
                  type="text"
                  required
                  value={newEntry.nombre}
                  onChange={(e) => setNewEntry({ ...newEntry, nombre: e.target.value })}
                  placeholder={activeTab === 'modulos' ? 'ej. Arquitectura de Datos y Data Lakehouse' : 'ej. Dr. Carlos Murillo'}
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  {activeTab === 'modulos' ? 'Programa Académico Perteneciente' : 'Área de Especialidad'}
                </label>
                <input
                  type="text"
                  value={newEntry.extra}
                  onChange={(e) => setNewEntry({ ...newEntry, extra: e.target.value })}
                  placeholder={activeTab === 'modulos' ? 'ej. Maestría en Big Data' : 'ej. Inteligencia Artificial'}
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-pill-ghost"
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-pill-dark" disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar en PostgreSQL'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
