import React, { useState } from 'react';
import { Plus, Edit2, Trash2 } from 'lucide-react';

export default function GestionUsuarios() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const currentAdminId = 1;

  const users = [
    { id: 1, nombre: 'Admin User', email: 'admin@gira.edu', rol: 'ADMIN', estado: 'Activo' },
    { id: 2, nombre: 'Ana Calidad', email: 'ana@gira.edu', rol: 'AUDITOR_CALIDAD', estado: 'Activo' },
    { id: 3, nombre: 'Carlos Academico', email: 'carlos@gira.edu', rol: 'DIRECTOR_ACADEMICO', estado: 'Activo' },
    { id: 4, nombre: 'Laura Finanzas', email: 'laura@gira.edu', rol: 'ANALISTA_FINANCIERO', estado: 'Inactivo' },
  ];

  return (
    <div className="module-container">
      <header className="mb-6 flex justify-between items-center">
        <h2 className="serif-heading text-ink-black" style={{ fontSize: '34px' }}>Gestión de Usuarios y Control RBAC</h2>
        <button 
          className="btn-pill-dark px-6 py-2 bg-ink-black text-paper-white rounded-full flex items-center gap-2 hover:opacity-90 transition-opacity"
          onClick={() => setIsModalOpen(true)}
        >
          <Plus size={16} /> Crear Nuevo Usuario
        </button>
      </header>

      <div className="floating-artifact bg-paper-white rounded-[24px] shadow-sm overflow-hidden mb-4">
        <table className="steep-table w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="p-4 font-medium text-sm text-gray-500">Nombre</th>
              <th className="p-4 font-medium text-sm text-gray-500">Email</th>
              <th className="p-4 font-medium text-sm text-gray-500">Rol</th>
              <th className="p-4 font-medium text-sm text-gray-500">Estado</th>
              <th className="p-4 font-medium text-sm text-gray-500">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-b hover:bg-gray-50">
                <td className="p-4">{u.nombre}</td>
                <td className="p-4">{u.email}</td>
                <td className="p-4">
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800 font-medium">{u.rol}</span>
                </td>
                <td className="p-4">{u.estado}</td>
                <td className="p-4 flex gap-2">
                  <button className="btn-pill-ghost p-2 text-gray-600 hover:bg-gray-200 rounded-full"><Edit2 size={16}/></button>
                  <button 
                    className="btn-pill-ghost text-red-600 p-2 hover:bg-red-50 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={u.id === currentAdminId}
                    title={u.id === currentAdminId ? "No puede auto-eliminarse" : "Eliminar"}
                  >
                    <Trash2 size={16}/>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <p className="text-sm text-amber-700 font-medium">⚠ El sistema debe mantener al menos un administrador activo</p>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-paper-white p-6 rounded-[24px] w-full max-w-md shadow-xl">
            <h3 className="text-xl font-bold mb-4">Crear Nuevo Usuario</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm mb-1">Nombre de usuario</label>
                <input type="text" className="form-input w-full p-2 border rounded-[16px]" />
              </div>
              <div>
                <label className="block text-sm mb-1">Correo</label>
                <input type="email" className="form-input w-full p-2 border rounded-[16px]" />
              </div>
              <div>
                <label className="block text-sm mb-1">Teléfono</label>
                <input type="tel" className="form-input w-full p-2 border rounded-[16px]" />
              </div>
              <div>
                <label className="block text-sm mb-1">Contraseña inicial</label>
                <input type="password" className="form-input w-full p-2 border rounded-[16px]" />
              </div>
              <div>
                <label className="block text-sm mb-1">Rol</label>
                <select className="form-input w-full p-2 border rounded-[16px]">
                  <option>ADMIN</option>
                  <option>AUDITOR_CALIDAD</option>
                  <option>DIRECTOR_ACADEMICO</option>
                  <option>ANALISTA_FINANCIERO</option>
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-pill-ghost px-4 py-2 text-gray-600 rounded-full hover:bg-gray-100" onClick={() => setIsModalOpen(false)}>Cancelar</button>
              <button className="btn-pill-dark px-4 py-2 bg-ink-black text-paper-white rounded-full">Crear Usuario</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
