import React, { useState, useEffect } from 'react';
import {
  GraduationCap, Users, BookOpen, Building2, Search, Plus, Trash2,
  CheckCircle2, RefreshCw, X
} from 'lucide-react';

import PageHeader from '../../components/shared/PageHeader';
import DataOpsTabs from './components/DataOpsTabs';
import ResponsiveTable from '../../components/shared/ResponsiveTable';

import { catalogApi } from '../../api/catalogApi';
import { sileoToast } from '../../services/sileoToast';

export default function MasterDataView() {
  const [activeTab, setActiveTab] = useState('students'); // 'students' | 'teachers' | 'modules' | 'institutions'
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Data states
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [modules, setModules] = useState([]);
  const [institutions, setInstitutions] = useState([]);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newRecordData, setNewRecordData] = useState({
    nombre_completo: '',
    codigo: '',
    ciudad: 'La Paz',
    area: 'Gestión',
    programa: 'Diplomado'
  });

  // Fetch data depending on activeTab
  const fetchData = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'students') {
        const res = await catalogApi.getEstudiantes({ q: searchQuery });
        setStudents(res?.data || []);
      } else if (activeTab === 'teachers') {
        const res = await catalogApi.getDocentes({ q: searchQuery });
        setTeachers(res?.data || []);
      } else if (activeTab === 'modules') {
        const res = await catalogApi.getModulos({ q: searchQuery });
        setModules(res?.data || []);
      } else if (activeTab === 'institutions') {
        const res = await catalogApi.getInstituciones({ q: searchQuery });
        setInstitutions(res?.data || []);
      }
    } catch (err) {
      console.warn('Error fetching catalog data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchData();
  };

  // Crear nuevo registro
  const handleCreateRecord = async (e) => {
    e.preventDefault();
    if (!newRecordData.nombre_completo.trim()) {
      sileoToast.warning({ title: 'Campo Requerido', description: 'El nombre es obligatorio.' });
      return;
    }

    try {
      if (activeTab === 'students') {
        await catalogApi.createEstudiante({
          nombre_completo: newRecordData.nombre_completo,
          codigo_estudiante: newRecordData.codigo,
          ciudad: newRecordData.ciudad
        });
        sileoToast.success({ title: 'Estudiante Creado', description: 'Añadido al catálogo maestro.' });
      } else if (activeTab === 'teachers') {
        await catalogApi.createDocente({
          nombre_completo: newRecordData.nombre_completo,
          area_especialidad: newRecordData.area
        });
        sileoToast.success({ title: 'Docente Registrado', description: 'Añadido al claustro docente.' });
      } else if (activeTab === 'modules') {
        await catalogApi.createModulo({
          nombre_modulo: newRecordData.nombre_completo,
          programa: newRecordData.programa,
          pos_code: newRecordData.codigo
        });
        sileoToast.success({ title: 'Módulo Creado', description: 'Añadido al plan curricular.' });
      }

      setIsModalOpen(false);
      setNewRecordData({ nombre_completo: '', codigo: '', ciudad: 'La Paz', area: 'Gestión', programa: 'Diplomado' });
      fetchData();
    } catch (err) {
      sileoToast.error({ title: 'Error al Crear', description: err.message });
    }
  };

  // Eliminar registro
  const handleDelete = async (id) => {
    try {
      if (activeTab === 'students') {
        await catalogApi.deleteEstudiante(id);
      } else if (activeTab === 'teachers') {
        await catalogApi.deleteDocente(id);
      } else if (activeTab === 'modules') {
        await catalogApi.deleteModulo(id);
      }
      sileoToast.success({ title: 'Registro Eliminado', description: `ID #${id} retirado del catálogo.` });
      fetchData();
    } catch (err) {
      sileoToast.error({ title: 'Falla al Eliminar', description: err.message });
    }
  };

  const tabsConfig = [
    { id: 'students', label: 'Estudiantes', icon: GraduationCap, count: students.length },
    { id: 'teachers', label: 'Claustro Docente', icon: Users, count: teachers.length },
    { id: 'modules', label: 'Módulos Curriculares', icon: BookOpen, count: modules.length },
    { id: 'institutions', label: 'Instituciones y Sedes', icon: Building2, count: institutions.length },
  ];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 8px 48px' }}>
      <PageHeader
        category="DATOS MAESTROS & GOBERNANZA"
        title="Catálogos Maestros de Desambiguación"
        subtitle="Mantenimiento de dimensiones canónicas (estudiantes, docentes, módulos curriculares e instituciones) que alimentan la reconciliación semántica."
        actions={
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              className="btn-pill-ghost"
              onClick={fetchData}
              disabled={isLoading}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
              <span>Actualizar</span>
            </button>
            <button
              className="btn-pill-dark"
              onClick={() => setIsModalOpen(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={16} />
              <span>+ Nuevo Registro</span>
            </button>
          </div>
        }
      />

      {/* Tabs */}
      <DataOpsTabs
        tabs={tabsConfig}
        activeTab={activeTab}
        onChangeTab={(tab) => {
          setActiveTab(tab);
          setSearchQuery('');
        }}
      />

      {/* Barra de Búsqueda */}
      <form
        onSubmit={handleSearchSubmit}
        style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '20px',
        }}
      >
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={18}
            style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-slate-gray)',
            }}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Buscar en ${tabsConfig.find(t => t.id === activeTab)?.label}...`}
            className="form-input"
            style={{
              width: '100%',
              paddingLeft: '42px',
              height: '42px',
              borderRadius: '9999px',
            }}
          />
        </div>
        <button type="submit" className="btn-pill-dark" style={{ height: '42px', padding: '0 20px' }}>
          Buscar
        </button>
      </form>

      {/* Tabla según Tab Activo */}
      <div>
        {/* TAB ESTUDIANTES */}
        {activeTab === 'students' && (
          <ResponsiveTable>
            <table className="steep-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre Completo</th>
                  <th>Código Estudiante</th>
                  <th>Ciudad</th>
                  <th>Nivel Académico</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {students.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-slate-gray)' }}>
                      No se encontraron estudiantes en el catálogo maestro.
                    </td>
                  </tr>
                ) : (
                  students.map((st) => (
                    <tr key={st.id_estudiante}>
                      <td><code>#{st.id_estudiante}</code></td>
                      <td style={{ fontWeight: 600 }}>{st.nombre_completo}</td>
                      <td><span className="badge-source">{st.codigo_estudiante || 'N/A'}</span></td>
                      <td>{st.ciudad || 'No especificada'}</td>
                      <td>{st.nivel_academico || 'Pregrado'}</td>
                      <td>
                        <button
                          className="btn-pill-ghost"
                          onClick={() => handleDelete(st.id_estudiante)}
                          style={{ padding: '4px 10px', fontSize: '11px', color: '#d9383a' }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </ResponsiveTable>
        )}

        {/* TAB DOCENTES */}
        {activeTab === 'teachers' && (
          <ResponsiveTable>
            <table className="steep-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre del Docente</th>
                  <th>Área de Especialidad</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {teachers.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-slate-gray)' }}>
                      No se encontraron docentes en el claustro.
                    </td>
                  </tr>
                ) : (
                  teachers.map((doc) => (
                    <tr key={doc.id_docente}>
                      <td><code>#{doc.id_docente}</code></td>
                      <td style={{ fontWeight: 600 }}>{doc.nombre_completo}</td>
                      <td><span className="badge-source">{doc.area_especialidad || 'General'}</span></td>
                      <td>
                        <button
                          className="btn-pill-ghost"
                          onClick={() => handleDelete(doc.id_docente)}
                          style={{ padding: '4px 10px', fontSize: '11px', color: '#d9383a' }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </ResponsiveTable>
        )}

        {/* TAB MÓDULOS */}
        {activeTab === 'modules' && (
          <ResponsiveTable>
            <table className="steep-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre del Módulo</th>
                  <th>Código POS</th>
                  <th>Programa</th>
                  <th>Institución</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {modules.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-slate-gray)' }}>
                      No se encontraron módulos curriculares.
                    </td>
                  </tr>
                ) : (
                  modules.map((m) => (
                    <tr key={m.id_modulo}>
                      <td><code>#{m.id_modulo}</code></td>
                      <td style={{ fontWeight: 600 }}>{m.nombre_modulo}</td>
                      <td><code>{m.pos_code || 'MOD-N/A'}</code></td>
                      <td>{m.programa || 'Programa General'}</td>
                      <td><span className="badge-source">{m.nombre_institucion || 'GiraGroup'}</span></td>
                      <td>
                        <button
                          className="btn-pill-ghost"
                          onClick={() => handleDelete(m.id_modulo)}
                          style={{ padding: '4px 10px', fontSize: '11px', color: '#d9383a' }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </ResponsiveTable>
        )}

        {/* TAB INSTITUCIONES */}
        {activeTab === 'institutions' && (
          <ResponsiveTable>
            <table className="steep-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre Institucional</th>
                  <th>Sigla</th>
                  <th>Tipo de Entidad</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {institutions.map((inst) => (
                  <tr key={inst.id_institucion}>
                    <td><code>#{inst.id_institucion}</code></td>
                    <td style={{ fontWeight: 600 }}>{inst.nombre}</td>
                    <td><span className="badge-source">{inst.sigla || 'INST'}</span></td>
                    <td>{inst.tipo}</td>
                    <td><span className="badge-status-completed">Activo</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ResponsiveTable>
        )}
      </div>

      {/* Modal de Nuevo Registro */}
      {isModalOpen && (
        <div className="modal-backdrop show" onClick={() => setIsModalOpen(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontFamily: 'var(--font-signifier)', margin: 0, fontSize: '20px' }}>
                Nuevo Registro ({tabsConfig.find(t => t.id === activeTab)?.label})
              </h3>
              <button className="btn-pill-ghost" onClick={() => setIsModalOpen(false)} style={{ padding: '4px' }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateRecord} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                  Nombre Completo / Denominación *
                </label>
                <input
                  type="text"
                  required
                  value={newRecordData.nombre_completo}
                  onChange={(e) => setNewRecordData({ ...newRecordData, nombre_completo: e.target.value })}
                  className="form-input"
                  placeholder="Ej: Lic. Juan Pérez / MOD-101..."
                />
              </div>

              {activeTab === 'students' && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                      Código Estudiante
                    </label>
                    <input
                      type="text"
                      value={newRecordData.codigo}
                      onChange={(e) => setNewRecordData({ ...newRecordData, codigo: e.target.value })}
                      className="form-input"
                      placeholder="EST-2026-001"
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                      Ciudad
                    </label>
                    <input
                      type="text"
                      value={newRecordData.ciudad}
                      onChange={(e) => setNewRecordData({ ...newRecordData, ciudad: e.target.value })}
                      className="form-input"
                      placeholder="La Paz / Santa Cruz / Cochabamba"
                    />
                  </div>
                </>
              )}

              {activeTab === 'teachers' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                    Área de Especialidad
                  </label>
                  <input
                    type="text"
                    value={newRecordData.area}
                    onChange={(e) => setNewRecordData({ ...newRecordData, area: e.target.value })}
                    className="form-input"
                    placeholder="Big Data / Finanzas / Gestión"
                  />
                </div>
              )}

              {activeTab === 'modules' && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                      Código POS
                    </label>
                    <input
                      type="text"
                      value={newRecordData.codigo}
                      onChange={(e) => setNewRecordData({ ...newRecordData, codigo: e.target.value })}
                      className="form-input"
                      placeholder="POS-302 / MOD-101"
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                      Programa Académico
                    </label>
                    <input
                      type="text"
                      value={newRecordData.programa}
                      onChange={(e) => setNewRecordData({ ...newRecordData, programa: e.target.value })}
                      className="form-input"
                      placeholder="Diplomado en Big Data"
                    />
                  </div>
                </>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn-pill-ghost" onClick={() => setIsModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-pill-dark">
                  Guardar en Catálogo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
