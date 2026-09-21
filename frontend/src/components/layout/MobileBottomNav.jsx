import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Cpu, GraduationCap, DollarSign, Database, Users, SlidersHorizontal, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function MobileBottomNav() {
  const { role, logout } = useAuth();

  const navItems = [
    { to: '/', label: 'CMI', icon: LayoutDashboard, exact: true },
    { to: '/dataops/procesamiento', label: 'DataOps', icon: Cpu },
    { to: '/academico/docentes', label: 'Académico', icon: GraduationCap },
    { to: '/financiero/recaudacion', label: 'Finanzas', icon: DollarSign },
  ];

  if (role === 'ADMIN') {
    navItems.push({ to: '/admin/catalogos', label: 'Catálogos', icon: Database });
    navItems.push({ to: '/admin/usuarios', label: 'Usuarios', icon: Users });
  }

  navItems.push({ to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal });

  return (
    <nav className="mobile-bottom-nav" aria-label="Navegación Móvil de Módulos">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}

      <button
        onClick={logout}
        type="button"
        className="mobile-nav-item"
        style={{ color: 'var(--color-alert-red)' }}
        title="Cerrar sesión"
      >
        <LogOut size={18} />
        <span>Salir</span>
      </button>
    </nav>
  );
}
