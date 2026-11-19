import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, Wand2, CheckSquare,
  GitMerge, GraduationCap, Star, BookOpen, TrendingUp, DollarSign,
  PieChart, Target, LineChart, Users, Settings, ChevronDown, ChevronRight,
  SlidersHorizontal, LogOut, FileSpreadsheet
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import GiraAnimatedLogoButton from '../components/GiraAnimatedLogoButton';
import { toV2Path, toV1Path } from '../utils/v2Routes';

const ROLE_MENUS = {
  AUDITOR_CALIDAD: [
    { id: 'ingesta', path: '/dataops/ingesta', label: '① Ingesta de Archivos', icon: FileUp },
    { id: 'beto', path: '/dataops/beto', label: '② Lectura de BETO', icon: Wand2 },
    { id: 'revision', path: '/dataops/revision', label: '③ Revisión Humana', icon: CheckSquare },
    { id: 'datos-maestros', path: '/dataops/datos-maestros', label: 'Datos Maestros & Catálogo', icon: GitMerge },
    { id: 'auditoria', path: '/admin/auditoria', label: 'Auditoría del Sistema', icon: ShieldCheck },
  ],
  DIRECTOR_ACADEMICO: [
    { id: 'rendimiento', path: '/academico/rendimiento', label: 'Alertas Tempranas (IF/THEN)', icon: GraduationCap },
    { id: 'docente', path: '/academico/docente', label: 'Desempeño Docente', icon: Star },
    { id: 'catalogo', path: '/academico/catalogo', label: 'Catálogo Curricular y Actas', icon: BookOpen },
    { id: 'proyeccion', path: '/academico/proyeccion', label: 'Proyección de Alumnos', icon: TrendingUp },
  ],
  ANALISTA_FINANCIERO: [
    { id: 'recaudacion', path: '/financiero/recaudacion', label: 'Cobranzas y Recaudación', icon: DollarSign },
    { id: 'cartera', path: '/financiero/cartera', label: 'Gestión de Cartera y Mora', icon: PieChart },
    { id: 'alertas', path: '/alertas-tempranas', label: 'Alertas Tempranas (IF/THEN)', icon: GraduationCap },
    { id: 'metas', path: '/financiero/metas', label: 'Metas vs. Ejecutado', icon: Target },
    { id: 'proyeccion', path: '/financiero/proyeccion', label: 'Proyección Financiera', icon: LineChart },
  ],
  ANALISTA_MARKETING: [
    { id: 'proyeccion', path: '/academico/proyeccion', label: 'Demanda y Viabilidad', icon: TrendingUp },
    { id: 'catalogo', path: '/academico/programas', label: 'Catálogo de Oferta', icon: BookOpen },
  ],
};

const ADMIN_OPERATIVE_CLUSTERS = [
  {
    id: 'dataops',
    label: 'Flujo DataOps & BETO',
    defaultOpen: true,
    items: [
      { path: '/dataops/ingesta', label: '① Ingesta de Archivos', icon: FileUp },
      { path: '/dataops/beto', label: '② Lectura de BETO', icon: Wand2 },
      { path: '/dataops/revision', label: '③ Revisión Humana', icon: CheckSquare },
      { path: '/dataops/datos-maestros', label: 'Datos Maestros & Catálogo', icon: GitMerge },
    ],
  },
  {
    id: 'acad',
    label: 'Área Académica',
    defaultOpen: false,
    items: [
      { path: '/academico/rendimiento', label: 'Alertas Tempranas (IF/THEN)', icon: GraduationCap },
      { path: '/academico/docente', label: 'Desempeño Docente', icon: Star },
      { path: '/academico/catalogo', label: 'Catálogo Curricular', icon: BookOpen },
      { path: '/academico/proyeccion', label: 'Proyección de Alumnos', icon: TrendingUp },
    ],
  },
  {
    id: 'fin',
    label: 'Área Financiera',
    defaultOpen: false,
    items: [
      { path: '/financiero/recaudacion', label: 'Recaudación', icon: DollarSign },
      { path: '/financiero/cartera', label: 'Cartera y Mora', icon: PieChart },
      { path: '/financiero/metas', label: 'Metas de Gestión', icon: Target },
      { path: '/financiero/proyeccion', label: 'Proyección Financiera', icon: LineChart },
    ],
  },
];

const AJUSTES_CLUSTER = {
  id: 'ajustes',
  label: 'Ajustes',
  defaultOpen: false,
  items: [
    { path: '/admin/usuarios', label: 'Gestión de Usuarios', icon: Users },
    { path: '/admin/catalogos', label: 'Catálogos Maestros', icon: Settings },
    { path: '/admin/auditoria', label: 'Auditoría del Sistema', icon: ShieldCheck },
    { path: '/ajustes', label: 'Ajustes del Sistema', icon: SlidersHorizontal },
  ],
};

function isRouteActive(itemPath, v1Pathname) {
  if (v1Pathname === itemPath || v1Pathname.startsWith(`${itemPath}/`)) return true;
  if (itemPath === '/dataops/beto' && /^\/dataops\/(?:texto|lote\/[^/]+\/(?:beto|texto))/.test(v1Pathname)) return true;
  if (itemPath === '/dataops/revision' && /^\/dataops\/lote\/[^/]+\/revision/.test(v1Pathname)) return true;
  return false;
}

export default function SidebarV2({
  isOpen = false,
  onClose,
  navigateV2,
  prefetchOnIntent,
}) {
  const { role, logout } = useAuth();
  const location = useLocation();
  const v1Pathname = toV1Path(location.pathname);

  const [expanded, setExpanded] = useState(() => {
    const init = { ajustes: false };
    ADMIN_OPERATIVE_CLUSTERS.forEach((c) => {
      init[c.id] = c.defaultOpen;
    });
    return init;
  });

  useEffect(() => {
    ADMIN_OPERATIVE_CLUSTERS.forEach((cluster) => {
      if (cluster.items.some((i) => isRouteActive(i.path, v1Pathname))) {
        setExpanded((prev) => (prev[cluster.id] ? prev : { ...prev, [cluster.id]: true }));
      }
    });
    if (AJUSTES_CLUSTER.items.some((i) => isRouteActive(i.path, v1Pathname))) {
      setExpanded((prev) => (prev.ajustes ? prev : { ...prev, ajustes: true }));
    }
  }, [v1Pathname]);

  const handleNav = (path) => {
    navigateV2(toV2Path(path));
    if (typeof window !== 'undefined' && window.innerWidth <= 960 && onClose) {
      onClose();
    }
  };

  const renderLink = (item) => {
    const Icon = item.icon;
    const active = isRouteActive(item.path, v1Pathname);
    return (
      <a
        key={item.path}
        href={toV2Path(item.path)}
        onClick={(e) => {
          e.preventDefault();
          handleNav(item.path);
        }}
        onMouseEnter={() => prefetchOnIntent?.(toV2Path(item.path))}
        onFocus={() => prefetchOnIntent?.(toV2Path(item.path))}
        className={`v2-sidebar-link ${active ? 'is-active' : ''}`}
      >
        <Icon size={15} style={{ flexShrink: 0 }} />
        <span>{item.label}</span>
      </a>
    );
  };

  return (
    <aside
      className={`v2-sidebar ${isOpen ? 'is-open' : ''}`}
      aria-label="Menú lateral en pastilla V2"
      aria-hidden={!isOpen}
      inert={!isOpen ? '' : undefined}
    >
      <div className="v2-sidebar-header">
        <div className="v2-sidebar-brand">
          <GiraAnimatedLogoButton
            isOpen={isOpen}
            onClick={onClose}
            ariaLabel="Ocultar menú lateral"
            title="Ocultar menú lateral"
          />
          <div onClick={() => handleNav('/dashboard')} style={{ minWidth: 0 }}>
            <div className="v2-sidebar-brand-title">
              GIRA <span className="v2-sidebar-brand-gold">Group</span>
            </div>
            <div className="v2-sidebar-brand-sub">BI &amp; Intelligence System</div>
          </div>
        </div>
      </div>

      <div className="v2-sidebar-scroll">
        {renderLink({ path: '/dashboard', label: 'Cuadro de Mando Integral', icon: LayoutDashboard })}
        {renderLink({ path: '/reportes', label: 'Centro de Reportes', icon: FileSpreadsheet })}

        {role === 'ADMIN'
          ? ADMIN_OPERATIVE_CLUSTERS.map((cluster) => {
              const groupOpen = Boolean(expanded[cluster.id]);
              return (
                <div key={cluster.id}>
                  <button
                    type="button"
                    className="v2-sidebar-group-btn"
                    onClick={() => setExpanded((prev) => ({ ...prev, [cluster.id]: !prev[cluster.id] }))}
                  >
                    <span>{cluster.label}</span>
                    {groupOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </button>
                  {groupOpen && cluster.items.map(renderLink)}
                </div>
              );
            })
          : (ROLE_MENUS[role] || []).map(renderLink)}
      </div>

      <div className="v2-sidebar-footer">
        {role === 'ADMIN' ? (
          <div>
            <button
              type="button"
              className="v2-sidebar-group-btn"
              onClick={() => setExpanded((prev) => ({ ...prev, ajustes: !prev.ajustes }))}
            >
              <span>{AJUSTES_CLUSTER.label}</span>
              {expanded.ajustes ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>
            {expanded.ajustes && AJUSTES_CLUSTER.items.map(renderLink)}
          </div>
        ) : (
          renderLink({ path: '/ajustes', label: 'Ajustes del Sistema', icon: SlidersHorizontal })
        )}

        <button
          type="button"
          onClick={logout}
          className="v2-sidebar-link"
          style={{ width: '100%', background: 'transparent', cursor: 'pointer' }}
        >
          <LogOut size={15} style={{ flexShrink: 0 }} />
          <span>Cerrar sesión</span>
        </button>

        <div className="v2-db-status-pill" aria-label="Estado de base de datos">
          <span className="v2-db-status-dot" aria-hidden="true" />
          <span>Base de datos: Conectada</span>
        </div>
      </div>
    </aside>
  );
}
