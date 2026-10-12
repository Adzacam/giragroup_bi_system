import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Cpu,
  GraduationCap,
  DollarSign,
  SlidersHorizontal,
  Menu,
  FileUp,
  Wand2,
  CheckSquare,
  Star,
  BookOpen,
  PieChart,
  Target,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function MobileBottomNav({ onOpenMenu, onCloseMenu, isMenuOpen = false }) {
  const { role } = useAuth();
  const location = useLocation();

  const getRoleItems = () => {
    if (role === 'AUDITOR_CALIDAD') {
      return [
        { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
        { to: '/dataops/ingesta', label: 'Ingesta', icon: FileUp, matchPrefix: '/dataops/ingesta' },
        { to: '/dataops/beto', label: 'BETO', icon: Wand2, matchPrefix: '/dataops/beto' },
        { to: '/dataops/revision', label: 'HITL', icon: CheckSquare, matchPrefix: '/dataops/revision' },
        { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
      ];
    }
    if (role === 'DIRECTOR_ACADEMICO') {
      return [
        { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
        { to: '/academico/rendimiento', label: 'Riesgo', icon: GraduationCap, matchPrefix: '/academico/rendimiento' },
        { to: '/academico/docente', label: 'Docentes', icon: Star, matchPrefix: '/academico/docente' },
        { to: '/academico/catalogo', label: 'Catálogo', icon: BookOpen, matchPrefix: '/academico/catalogo' },
        { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
      ];
    }
    if (role === 'ANALISTA_FINANCIERO') {
      return [
        { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
        { to: '/financiero/recaudacion', label: 'Cobranza', icon: DollarSign, matchPrefix: '/financiero/recaudacion' },
        { to: '/financiero/cartera', label: 'Cartera', icon: PieChart, matchPrefix: '/financiero/cartera' },
        { to: '/financiero/metas', label: 'Metas', icon: Target, matchPrefix: '/financiero/metas' },
        { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
      ];
    }
    // Default / ADMIN: Core executive modules + Menu drawer trigger
    return [
      { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
      { to: '/dataops/ingesta', label: 'DataOps', icon: Cpu, matchPrefix: '/dataops' },
      { to: '/academico/rendimiento', label: 'Académico', icon: GraduationCap, matchPrefix: '/academico' },
      { to: '/financiero/recaudacion', label: 'Finanzas', icon: DollarSign, matchPrefix: '/financiero' },
      { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
    ];
  };

  const navItems = getRoleItems();

  return (
    <nav className="mobile-bottom-nav" aria-label="Navegación Móvil de Módulos">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isSectionActive =
          location.pathname === item.to ||
          (item.matchPrefix && location.pathname.startsWith(item.matchPrefix)) ||
          (item.to === '/dataops/beto' && /^\/dataops\/lote\/[^/]+\/beto/.test(location.pathname)) ||
          (item.to === '/dataops/revision' && (/^\/dataops\/lote\/[^/]+\/revision/.test(location.pathname) || location.pathname === '/dataops/auditoria-humana')) ||
          (item.to === '/ajustes' && location.pathname.startsWith('/admin'));

        return (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => {
              if (onCloseMenu) onCloseMenu();
            }}
            className={({ isActive }) =>
              `mobile-nav-item ${!isMenuOpen && (isActive || isSectionActive) ? 'active' : ''}`
            }
          >
            <Icon size={17} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}

      {onOpenMenu && (
        <button
          onClick={onOpenMenu}
          type="button"
          className={`mobile-nav-item ${isMenuOpen ? 'active' : ''}`}
          title="Abrir todos los módulos"
          aria-label="Abrir menú completo de módulos"
        >
          <Menu size={17} />
          <span>Menú</span>
        </button>
      )}
    </nav>
  );
}

