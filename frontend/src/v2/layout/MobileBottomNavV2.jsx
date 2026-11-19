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
        { to: '/v2/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/v2/dashboard' },
        { to: '/v2/dataops/ingesta', label: 'Ingesta', icon: FileUp, matchPrefix: '/v2/dataops/ingesta' },
        { to: '/v2/dataops/beto', label: 'BETO', icon: Wand2, matchPrefix: '/v2/dataops/beto' },
        { to: '/v2/dataops/revision', label: 'Revisión', icon: CheckSquare, matchPrefix: '/v2/dataops/revision' },
        { to: '/v2/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/v2/ajustes' },
      ];
    }
    if (role === 'DIRECTOR_ACADEMICO') {
      return [
        { to: '/v2/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/v2/dashboard' },
        { to: '/v2/academico/rendimiento', label: 'Riesgo', icon: GraduationCap, matchPrefix: '/v2/academico/rendimiento' },
        { to: '/v2/academico/docente', label: 'Docentes', icon: Star, matchPrefix: '/v2/academico/docente' },
        { to: '/v2/academico/catalogo', label: 'Catálogo', icon: BookOpen, matchPrefix: '/v2/academico/catalogo' },
        { to: '/v2/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/v2/ajustes' },
      ];
    }
    if (role === 'ANALISTA_FINANCIERO') {
      return [
        { to: '/v2/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/v2/dashboard' },
        { to: '/v2/financiero/recaudacion', label: 'Cobranza', icon: DollarSign, matchPrefix: '/v2/financiero/recaudacion' },
        { to: '/v2/financiero/cartera', label: 'Cartera', icon: PieChart, matchPrefix: '/v2/financiero/cartera' },
        { to: '/v2/financiero/metas', label: 'Metas', icon: Target, matchPrefix: '/v2/financiero/metas' },
        { to: '/v2/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/v2/ajustes' },
      ];
    }
    if (role === 'ANALISTA_MARKETING') {
      return [
        { to: '/v2/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/v2/dashboard' },
        { to: '/v2/academico/proyeccion', label: 'Demanda', icon: TrendingUp, matchPrefix: '/v2/academico/proyeccion' },
        { to: '/v2/academico/programas', label: 'Catálogo', icon: BookOpen, matchPrefix: '/v2/academico/programas' },
        { to: '/v2/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/v2/ajustes' },
      ];
    }
    return [
      { to: '/v2/dashboard', label: 'CMI', icon: LayoutDashboard, matchPrefix: '/v2/dashboard' },
      { to: '/v2/dataops/ingesta', label: 'DataOps', icon: Cpu, matchPrefix: '/v2/dataops' },
      { to: '/v2/academico/rendimiento', label: 'Académico', icon: GraduationCap, matchPrefix: '/v2/academico' },
      { to: '/v2/financiero/recaudacion', label: 'Finanzas', icon: DollarSign, matchPrefix: '/v2/financiero' },
      { to: '/v2/ajustes', label: 'Ajustes', icon: SlidersHorizontal, matchPrefix: '/v2/ajustes' },
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
