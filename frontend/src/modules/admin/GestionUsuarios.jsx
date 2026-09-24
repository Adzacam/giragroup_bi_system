import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Shield, UserCheck, AlertTriangle, X, User } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { usersApi } from '../../api/usersApi';
import { useAuth } from '../../context/AuthContext';
import useKineticScroll from '../../hooks/useKineticScroll';
import ProfileModal from '../../components/profile/ProfileModal';

const FALLBACK_USERS = [
  { id: 1, username: 'admin_general', email: 'admin.general@giragroup.bo', role: 'ADMIN', is_active: true },
  { id: 2, username: 'auditor_dataops', email: 'auditor.dataops@giragroup.bo', role: 'AUDITOR_CALIDAD', is_active: true },
  { id: 3, username: 'dir_academica', email: 'direccion.academica@giragroup.bo', role: 'DIRECTOR_ACADEMICO', is_active: true },
  { id: 4, username: 'analista_fin', email: 'analista.finanzas@giragroup.bo', role: 'ANALISTA_FINANCIERO', is_active: true },
];

export default function GestionUsuarios() {
  useKineticScroll();
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState(FALLBACK_USERS);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phone: '',
    password: '',
    role: 'AUDITOR_CALIDAD',
  });

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await usersApi.getUsers();
      if (Array.isArray(data) && data.length > 0) {
        setUsers(data);
      }
    } catch (err) {
      console.warn('Backend users unavailable, keeping local seeded data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const created = await usersApi.createUser(formData);
      setSuccessMsg(`Usuario ${created.username || formData.username} creado exitosamente.`);
      setIsModalOpen(false);
      setFormData({ username: '', email: '', phone: '', password: '', role: 'AUDITOR_CALIDAD' });
      loadUsers();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Error al crear el usuario en la base de datos.');
    }
  };

  const handleDeleteUser = async (userToDelete) => {
    // Anti-orphan client-side checks
    if (userToDelete.id === currentUser?.id || userToDelete.email === currentUser?.email) {
      setErrorMsg('No puedes auto-eliminar tu propia cuenta de administrador.');
      return;
    }

    const adminCount = users.filter((u) => u.role === 'ADMIN').length;
    if (userToDelete.role === 'ADMIN' && adminCount <= 1) {
      setErrorMsg('Acción denegada: No se puede dejar el sistema sin al menos un Administrador activo.');
      return;
    }

    if (!window.confirm(`¿Estás seguro de revocar y eliminar a ${userToDelete.username} (${userToDelete.email})?`)) {
      return;
    }

    try {
      await usersApi.deleteUser(userToDelete.id);
      setSuccessMsg(`Usuario ${userToDelete.username} eliminado correctamente.`);
      loadUsers();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Error al eliminar usuario.');
    }
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'ADMIN':
        return { bg: '#fee2e2', color: 'var(--color-alert-red)', label: 'Administrador' };
      case 'AUDITOR_CALIDAD':
        return { bg: 'var(--color-blush-peach)', color: 'var(--color-sienna-brown)', label: 'Auditor DataOps' };
      case 'DIRECTOR_ACADEMICO':
        return { bg: '#e0f2fe', color: '#0369a1', label: 'Director Académico' };
      case 'ANALISTA_FINANCIERO':
        return { bg: '#dcfce7', color: 'var(--color-alert-green)', label: 'Analista Finanzas' };
      default:
        return { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', label: role };
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="GOBERNANZA &amp; SEGURIDAD"
        title="Gestión de Usuarios y Control"
        italicWord="RBAC"
        subtitle="Administración de credenciales de acceso institucional bajo el Principio de Mínimo Privilegio (PoLP) con salvaguardas anti-huérfano."
        action={
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-pill-dark"
            type="button"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={16} /> Crear Nuevo Usuario
          </button>
        }
      />

      {errorMsg && (
        <div
          style={{
            padding: '14px 18px',
            marginBottom: '20px',
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: 'var(--color-alert-red)',
            borderRadius: 'var(--radius-inputs)',
            fontSize: '13.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <AlertTriangle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            padding: '14px 18px',
            marginBottom: '20px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #bbf7d0',
            color: 'var(--color-alert-green)',
            borderRadius: 'var(--radius-inputs)',
            fontSize: '13.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <UserCheck size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* ── Tabla Principal RBAC ────────────────────────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre de Usuario</th>
              <th>Correo Institucional</th>
              <th>Rol del Sistema</th>
              <th>Estado</th>
              <th style={{ textAlign: 'right' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const badge = getRoleBadge(u.role);
              const isSelf = u.id === currentUser?.id || u.email === currentUser?.email;
              return (
                <tr key={u.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                    #{u.id}
                  </td>
                  <td>
                    <strong>{u.username}</strong>
                    {isSelf && (
                      <span
                        style={{
                          marginLeft: '8px',
                          fontSize: '10.5px',
                          padding: '1px 6px',
                          backgroundColor: 'var(--color-mist-gray)',
                          borderRadius: '4px',
                          color: 'var(--color-slate-gray)',
                        }}
                      >
                        (Tu sesión)
                      </span>
                    )}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{u.email}</td>
                  <td>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '3px 10px',
                        borderRadius: '9999px',
                        fontSize: '11.5px',
                        fontWeight: 600,
                        backgroundColor: badge.bg,
                        color: badge.color,
                      }}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '12.5px',
                        color: u.is_active !== false ? 'var(--color-alert-green)' : 'var(--color-slate-gray)',
                      }}
                    >
                      <span
                        style={{
                          width: '7px',
                          height: '7px',
                          borderRadius: '50%',
                          backgroundColor: u.is_active !== false ? 'var(--color-alert-green)' : '#9ca3af',
                        }}
                      />
                      {u.is_active !== false ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        onClick={() => setIsProfileModalOpen(true)}
                        className="btn-pill-ghost"
                        style={{
                          padding: '6px 12px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '12px',
                          color: 'var(--color-ink-black)',
                        }}
                        title="Ver Perfil y Gestión de Credenciales"
                        type="button"
                      >
                        <User size={13} style={{ color: 'var(--color-gira-gold)' }} />
                        <span>Perfil</span>
                      </button>

                      <button
                        onClick={() => handleDeleteUser(u)}
                        disabled={isSelf}
                        className="btn-pill-ghost"
                        style={{
                          padding: '6px 10px',
                          color: isSelf ? '#d1d5db' : 'var(--color-alert-red)',
                          borderColor: isSelf ? '#f3f4f6' : '#fee2e2',
                          cursor: isSelf ? 'not-allowed' : 'pointer',
                        }}
                        title={isSelf ? 'No puedes auto-eliminar tu propia cuenta' : 'Revocar usuario'}
                        type="button"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ResponsiveTable>

      <div
        style={{
          marginTop: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '12.5px',
          color: 'var(--color-slate-gray)',
        }}
      >
        <Shield size={14} color="var(--color-sienna-brown)" />
        <span>Salvaguarda anti-huérfano activa: El sistema prohíbe eliminar al último administrador registrado.</span>
      </div>

      {/* ── Modal de Creación de Usuario ────────────────────── */}
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
              padding: '32px',
              borderRadius: 'var(--radius-cards)',
              backgroundColor: 'var(--color-paper-white)',
              boxShadow: 'var(--shadow-modal)',
              animation: 'modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 className="serif-heading" style={{ fontSize: '22px', margin: 0 }}>
                Crear Nuevo Usuario
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                type="button"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Nombre de usuario
                </label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="ej. auditor_secundario"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Correo Institucional
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="usuario@giragroup.bo"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Teléfono (Opcional para SMS 2FA)
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+591 70000000"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Contraseña Inicial
                </label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="Mínimo 8 caracteres"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                  Rol del Sistema (PoLP)
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="form-input"
                  style={{ cursor: 'pointer' }}
                >
                  <option value="AUDITOR_CALIDAD">AUDITOR_CALIDAD (DataOps &amp; Pipeline)</option>
                  <option value="DIRECTOR_ACADEMICO">DIRECTOR_ACADEMICO (Retención &amp; Curricular)</option>
                  <option value="ANALISTA_FINANCIERO">ANALISTA_FINANCIERO (Cobranzas &amp; Flujo)</option>
                  <option value="ADMIN">ADMIN (Acceso Total)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-pill-ghost"
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-pill-dark">
                  Guardar Usuario
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Profile & Password Management Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
      />
    </div>
  );
}
