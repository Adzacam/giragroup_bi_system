import React, { useState } from 'react';
import { Database, Plus, Search, CheckCircle, RefreshCw, X } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_CATALOGS = {
  modulos: [
    { id: 101, codigo: 'POS-101', nombre: 'Maestría en Big Data & DataOps', tipo: 'Postgrado', institucion: 'GiraGroup Central', estado: 'Vigente' },
    { id: 102, codigo: 'POS-102', nombre: 'Diplomado en Machine Learning Aplicado', tipo: 'Diplomado', institucion: 'Escuela de IA', estado: 'Vigente' },
    { id: 103, codigo: 'DIP-201', nombre: 'Gestión Financiera para Directivos', tipo: 'Diplomado', institucion: 'Escuela de Negocios', estado: 'Vigente' },
    { id: 104, codigo: 'EXP-301', nombre: 'Programa Experto en Python Analytics', tipo: 'Experto', institucion: 'Educación Continua', estado: 'Vigente' },
  ],
  docentes: [
    { id: 1, codigo: 'DOC-109', nombre: 'Dr. Carlos Alberto Gómez Murillo', especialidad: 'Arquitectura de Datos & MLOps', actas: 14, estado: 'Activo' },
    { id: 2, codigo: 'DOC-112', nombre: 'MSc. Valeria Quiroga Morales', especialidad: 'Modelos de Riesgo Financiero', actas: 9, estado: 'Activo' },
    { id: 3, codigo: 'DOC-120', nombre: 'Ing. Fernando Tapia Dávalos', especialidad: 'Sistemas de Recomendación', actas: 12, estado: 'Activo' },
    { id: 4, codigo: 'DOC-135', nombre: 'Lic. Mariana Siles Benítez', especialidad: 'Auditoría Forense y Control', actas: 6, estado: 'Activo' },
  ],
  categorias: [
    { id: 1, codigo: 'CAT-01', nombre: 'Matrículas de Postgrado', tipo: 'INGRESO', centroCosto: 'CC-100', estado: 'Canónico' },
    { id: 2, codigo: 'CAT-02', nombre: 'Cuotas Mensuales Programas', tipo: 'INGRESO', centroCosto: 'CC-101', estado: 'Canónico' },
    { id: 3, codigo: 'CAT-03', nombre: 'Honorarios Docentes de Cátedra', tipo: 'EGRESO', centroCosto: 'CC-200', estado: 'Canónico' },
    { id: 4, codigo: 'CAT-04', nombre: 'Licenciamiento Cloud & GPU', tipo: 'EGRESO', centroCosto: 'CC-300', estado: 'Canónico' },
  ],
};

export default function CatalogosMaestros() {
  useKineticScroll();
  const [activeTab, setActiveTab] = useState('modulos');
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [data, setData] = useState(MOCK_CATALOGS);
  const [newEntry, setNewEntry] = useState({ codigo: '', nombre: '', extra: '' });

  const currentList = data[activeTab].filter((item) =>
    item.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.codigo.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAdd = (e) => {
    e.preventDefault();
    const created = {
      id: Date.now(),
      codigo: newEntry.codigo,
      nombre: newEntry.nombre,
      tipo: newEntry.extra || 'Canónico',
      institucion: 'GiraGroup Central',
      especialidad: newEntry.extra,
      centroCosto: newEntry.extra,
      actas: 0,
      estado: 'Vigente',
    };
    setData((prev) => ({
      ...prev,
      [activeTab]: [created, ...prev[activeTab]],
    }));
    setIsModalOpen(false);
    setNewEntry({ codigo: '', nombre: '', extra: '' });
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="DIMENSIONES CANÓNICAS POSTGRESQL"
        title="Catálogos Maestros"
        italicWord="CRUD"
        subtitle="Mantenimiento y sincronización de tablas dimensionales canónicas que alimentan las llaves foráneas del modelo estrella."
        action={
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-pill-dark"
            type="button"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={16} /> Añadir Registro
          </button>
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
          Módulos y Programas
        </button>
        <button
          onClick={() => { setActiveTab('docentes'); setSearchTerm(''); }}
          className={activeTab === 'docentes' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '8px 18px', fontSize: '13.5px' }}
        >
          Plantel Docente
        </button>
        <button
          onClick={() => { setActiveTab('categorias'); setSearchTerm(''); }}
          className={activeTab === 'categorias' ? 'btn-pill-dark' : 'btn-pill-ghost'}
          type="button"
          style={{ padding: '8px 18px', fontSize: '13.5px' }}
        >
          Categorías Financieras
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
            placeholder="Buscar por código o nombre..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
          Total registros: <strong>{currentList.length}</strong>
        </div>
      </div>

      {/* ── Tabla de Catálogo ────────────────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Código Canónico</th>
              <th>Descripción / Nombre</th>
              {activeTab === 'modulos' && <th>Tipo Programa</th>}
              {activeTab === 'docentes' && <th>Área Especialidad</th>}
              {activeTab === 'categorias' && <th>Tipo Rubro</th>}
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {currentList.map((row) => (
              <tr key={row.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                  {row.codigo}
                </td>
                <td>{row.nombre}</td>
                {activeTab === 'modulos' && <td>{row.tipo}</td>}
                {activeTab === 'docentes' && <td>{row.especialidad}</td>}
                {activeTab === 'categorias' && (
                  <td>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        backgroundColor: row.tipo === 'INGRESO' ? '#dcfce7' : '#fee2e2',
                        color: row.tipo === 'INGRESO' ? 'var(--color-alert-green)' : 'var(--color-alert-red)',
                      }}
                    >
                      {row.tipo}
                    </span>
                  </td>
                )}
                <td>
                  <span className="badge-status badge-status-completed">
                    <CheckCircle size={12} /> {row.estado}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>

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
              maxWidth: '460px',
              padding: '30px',
              borderRadius: 'var(--radius-cards)',
              backgroundColor: 'var(--color-paper-white)',
              boxShadow: 'var(--shadow-modal)',
              animation: 'modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
                Nuevo Registro ({activeTab})
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
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Código Canónico
                </label>
                <input
                  type="text"
                  required
                  value={newEntry.codigo}
                  onChange={(e) => setNewEntry({ ...newEntry, codigo: e.target.value })}
                  placeholder="ej. POS-105 o DOC-140"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Nombre / Descripción
                </label>
                <input
                  type="text"
                  required
                  value={newEntry.nombre}
                  onChange={(e) => setNewEntry({ ...newEntry, nombre: e.target.value })}
                  placeholder="Descripción canónica completa"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Atributo Secundario (Especialidad / Tipo / Centro Costo)
                </label>
                <input
                  type="text"
                  value={newEntry.extra}
                  onChange={(e) => setNewEntry({ ...newEntry, extra: e.target.value })}
                  placeholder="ej. Maestría o CC-400"
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-pill-ghost"
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-pill-dark">
                  Guardar en PostgreSQL
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
