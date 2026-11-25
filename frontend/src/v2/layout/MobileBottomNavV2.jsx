import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Cpu, GraduationCap, DollarSign, SlidersHorizontal,
  FileUp, Wand2, CheckSquare, Star, BookOpen, PieChart, Target, TrendingUp
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function MobileBottomNavV2({
  isMenuOpen = false,
  navigateV2,
  prefetchOnIntent,
}) {
  const { role } = useAuth();
  const location = useLocation();

  const getRoleItems = () => {
    if (role === 'AUDITOR_CALIDAD') {
      return [
        { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
        { to: '/dataops/ingesta', label: 'Ingesta', icon: FileUp, matchPrefix: '/dataops/ingesta' },
        { to: '/dataops/beto', label: 'BETO', icon: Wand2, matchPrefix: '/dataops/beto' },
        { to: '/dataops/revision', label: 'Revisión', icon: CheckSquare, matchPrefix: '/dataops/revision' },
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
    if (role === 'ANALISTA_MARKETING') {
      return [
        { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
        { to: '/academico/proyeccion', label: 'Demanda', icon: TrendingUp, matchPrefix: '/academico/proyeccion' },
        { to: '/academico/programas', label: 'Catálogo', icon: BookOpen, matchPrefix: '/academico/programas' },
        { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
      ];
    }
    return [
      { to: '/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/dashboard' },
      { to: '/dataops/ingesta', label: 'DataOps', icon: Cpu, matchPrefix: '/dataops' },
      { to: '/academico/rendimiento', label: 'Académico', icon: GraduationCap, matchPrefix: '/academico' },
      { to: '/financiero/recaudacion', label: 'Finanzas', icon: DollarSign, matchPrefix: '/financiero' },
      { to: '/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/ajustes' },
    ];
  };

  const navItems = getRoleItems();
  const activeIdx = navItems.findIndex(
    (item) =>
      location.pathname === item.to ||
      (item.matchPrefix && location.pathname.startsWith(item.matchPrefix))
  );

  return (
    <div className="v2-mobile-bottom-wrap" aria-label="Navegación Móvil en Pastilla V2">
      <nav className="v2-mobile-pill">
        {navItems.map((item, idx) => {
          const Icon = item.icon;
          const isActive = !isMenuOpen && idx === activeIdx;
          return (
            <button
              key={item.to}
              type="button"
              onClick={() => {
                const direction =
                  activeIdx !== -1 && idx !== activeIdx
                    ? idx > activeIdx
                      ? 'sibling-forward'
                      : 'sibling-backward'
                    : null;
                navigateV2(item.to, { direction });
              }}
              onMouseEnter={() => prefetchOnIntent?.(item.to)}
              className={`v2-mobile-pill-item ${isActive ? 'is-active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon size={15} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
