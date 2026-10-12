import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, FileText, Wand2, CheckSquare,
  GitMerge, Cpu, GraduationCap, Star, BookOpen,
  TrendingUp, DollarSign, PieChart, Target, LineChart,
  Users, Settings, ChevronDown, ChevronRight, Activity, SlidersHorizontal, LogOut, X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

/* ─── Role-based menu definitions for non-admin roles ─── */
const ROLE_MENUS = {
  AUDITOR_CALIDAD: [
    { id: 'ingesta',          path: '/dataops/ingesta',          label: '① Ingesta de Archivos',            icon: FileUp },
    { id: 'texto',            path: '/dataops/texto',            label: '② Texto Plano Estructurado',        icon: FileText },
    { id: 'beto',             path: '/dataops/beto',             label: '③ Lectura de BETO',                 icon: Wand2 },
    { id: 'revision',         path: '/dataops/revision',         label: '④ Revisión Humana (HITL)',         icon: CheckSquare },
    { id: 'beto-ner',         path: '/dataops/beto-ner',         label: 'Laboratorio BETO NER',              icon: Cpu },
    { id: 'auditoria-humana', path: '/dataops/auditoria-humana', label: 'Consola HITL e Inconsistencias',    icon: Activity },
    { id: 'datos-maestros',   path: '/dataops/datos-maestros',   label: 'Datos Maestros & Catálogo',        icon: GitMerge },
    { id: 'auditoria',        path: '/admin/auditoria',          label: 'Auditoría del Sistema',             icon: ShieldCheck },
  ],
  DIRECTOR_ACADEMICO: [
    { id: 'rendimiento',   path: '/academico/rendimiento',   label: 'Rendimiento y Alertas',             icon: GraduationCap },
    { id: 'docente',       path: '/academico/docente',       label: 'Desempeño Docente',                 icon: Star },
    { id: 'catalogo',      path: '/academico/catalogo',      label: 'Catálogo Curricular y Actas',       icon: BookOpen },
    { id: 'proyeccion',    path: '/academico/proyeccion',    label: 'Proyección de Alumnos',             icon: TrendingUp },
  ],
  ANALISTA_FINANCIERO: [
    { id: 'recaudacion',   path: '/financiero/recaudacion',  label: 'Cobranzas y Recaudación',           icon: DollarSign },
    { id: 'cartera',       path: '/financiero/cartera',      label: 'Gestión de Cartera y Mora',         icon: PieChart },
    { id: 'metas',         path: '/financiero/metas',        label: 'Metas vs. Ejecutado',               icon: Target },
    { id: 'proyeccion',    path: '/financiero/proyeccion',   label: 'Proyección Financiera',             icon: LineChart },
  ],
};

/* ─── Admin Operative clusters (Top Scrollable Section) ─── */
const ADMIN_OPERATIVE_CLUSTERS = [
  {
    id: 'dataops', label: 'Flujo DataOps & BETO', icon: ShieldCheck, defaultOpen: true,
    items: [
      { path: '/dataops/ingesta',          label: '① Ingesta de Archivos',            icon: FileUp },
      { path: '/dataops/texto',            label: '② Texto Plano Estructurado',        icon: FileText },
      { path: '/dataops/beto',             label: '③ Lectura de BETO',                 icon: Wand2 },
      { path: '/dataops/revision',         label: '④ Revisión Humana (HITL)',         icon: CheckSquare },
      { path: '/dataops/beto-ner',         label: 'Laboratorio BETO NER',              icon: Cpu },
      { path: '/dataops/auditoria-humana', label: 'Consola HITL e Inconsistencias',    icon: Activity },
      { path: '/dataops/datos-maestros',   label: 'Datos Maestros & Catálogo',        icon: GitMerge },
    ],
  },
  {
    id: 'acad', label: 'Área Académica', icon: GraduationCap, defaultOpen: false,
    items: [
      { path: '/academico/rendimiento',   label: 'Rendimiento y Alertas',      icon: GraduationCap },
      { path: '/academico/docente',       label: 'Desempeño Docente',          icon: Star },
      { path: '/academico/catalogo',      label: 'Catálogo Curricular',        icon: BookOpen },
      { path: '/academico/proyeccion',    label: 'Proyección de Alumnos',      icon: TrendingUp },
    ],
  },
  {
    id: 'fin', label: 'Área Financiera', icon: DollarSign, defaultOpen: false,
    items: [
      { path: '/financiero/recaudacion',  label: 'Recaudación',               icon: DollarSign },
      { path: '/financiero/cartera',      label: 'Cartera y Mora',            icon: PieChart },
      { path: '/financiero/metas',        label: 'Metas de Gestión',          icon: Target },
      { path: '/financiero/proyeccion',   label: 'Proyección Financiera',     icon: LineChart },
    ],
  },
];

/* ─── Ajustes Cluster (Pinned at the Bottom of Sidebar) ─── */
const AJUSTES_CLUSTER = {
  id: 'ajustes', label: 'Ajustes', icon: Settings, defaultOpen: false,
  items: [
    { path: '/admin/usuarios',          label: 'Gestión de Usuarios',        icon: Users },
    { path: '/admin/catalogos',         label: 'Catálogos Maestros',         icon: Settings },
    { path: '/admin/auditoria',         label: 'Auditoría del Sistema',      icon: ShieldCheck },
    { path: '/ajustes',                 label: 'Ajustes del Sistema',        icon: SlidersHorizontal },
  ],
};

function isRouteItemActive(itemPath, pathname) {
  if (pathname === itemPath || pathname.startsWith(`${itemPath}/`)) return true;
  if (itemPath === '/dataops/texto' && /^\/dataops\/lote\/[^/]+\/texto/.test(pathname)) return true;
  if (itemPath === '/dataops/beto' && /^\/dataops\/lote\/[^/]+\/beto/.test(pathname)) return true;
  if (itemPath === '/dataops/revision' && /^\/dataops\/lote\/[^/]+\/revision/.test(pathname)) return true;
  return false;
}

export default function Sidebar({ collapsed, isOpen, onClose, onToggle }) {
  const { role, logout } = useAuth();
  const location = useLocation();

  const [isMobileViewport, setIsMobileViewport] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(max-width: 960px)').matches || window.innerWidth <= 960
      : false
  );

  useEffect(() => {
    const media = window.matchMedia('(max-width: 960px)');
    const updateViewport = () => {
      setIsMobileViewport(media.matches || window.innerWidth <= 960);
    };
    updateViewport();
    media.addEventListener('change', updateViewport);
    window.addEventListener('resize', updateViewport, { passive: true });
    return () => {
      media.removeEventListener('change', updateViewport);
      window.removeEventListener('resize', updateViewport);
    };
  }, []);

  // On mobile/tablet (<= 960px) or when mobile drawer is open, never render in collapsed icon-only mode
  const isEffectiveCollapsed = (isOpen || isMobileViewport) ? false : Boolean(collapsed);

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const initial = { ajustes: false };
    ADMIN_OPERATIVE_CLUSTERS.forEach(c => { initial[c.id] = c.defaultOpen; });
    return initial;
  });

  // Automatically expand the cluster containing the active route
  useEffect(() => {
    ADMIN_OPERATIVE_CLUSTERS.forEach(cluster => {
      if (cluster.items.some(item => isRouteItemActive(item.path, location.pathname))) {
        setExpandedGroups(prev => (prev[cluster.id] ? prev : { ...prev, [cluster.id]: true }));
      }
    });
    if (AJUSTES_CLUSTER.items.some(item => isRouteItemActive(item.path, location.pathname))) {
      setExpandedGroups(prev => (prev.ajustes ? prev : { ...prev, ajustes: true }));
    }
  }, [location.pathname]);

  const toggleGroup = (id) => {
    if (isEffectiveCollapsed && onToggle) {
      onToggle(); // expand desktop sidebar if collapsed
      setExpandedGroups(prev => ({ ...prev, [id]: true }));
      return;
    }
    setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleLinkClick = () => {
    if (onClose) onClose();
  };

  const handleLogoutClick = () => {
    if (onClose) onClose();
    logout();
  };

  const isAdmin = role === 'ADMIN';
  const menuItems = !isAdmin ? (ROLE_MENUS[role] || []) : [];

  const isAjustesExpanded = expandedGroups['ajustes'];
  const hasAjustesActive = AJUSTES_CLUSTER.items.some(i => isRouteItemActive(i.path, location.pathname));

  return (
    <aside
      className={`app-sidebar ${isEffectiveCollapsed ? 'collapsed' : ''} ${isOpen ? 'open' : ''}`}
      aria-label="Menú lateral de módulos"
    >
      {/* ─── Mobile/Tablet Drawer Header (<= 960px, controlled via CSS) ─────────── */}
      <div className="sidebar-mobile-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <div
            style={{
              width: '30px',
              height: '30px',
              borderRadius: '8px',
              backgroundColor: '#0C1E33',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              border: '1px solid rgba(217, 155, 38, 0.35)',
            }}
          >
            <span style={{ color: '#D99B26', fontWeight: 800, fontSize: '13px', fontFamily: 'var(--font-sohne)' }}>
              G
            </span>
          </div>
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: '13.5px',
                fontWeight: 700,
                color: 'var(--color-ink-black)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                lineHeight: 1.2,
              }}
            >
              Módulos del Sistema
            </div>
            <div
              style={{
                fontSize: '10px',
                fontWeight: 600,
                color: 'var(--color-slate-gray)',
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
                whiteSpace: 'nowrap',
              }}
            >
              GIRA Group BI
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          type="button"
          className="sidebar-close-btn"
          title="Cerrar menú"
          aria-label="Cerrar menú lateral"
        >
          <X size={17} />
        </button>
      </div>

      {/* ─── Upper Section: Main Navigation (Scrollable) ─────────── */}
      <div className="sidebar-scroll-area">
        <div>
          {/* Dashboard link */}
          <div style={{ padding: isEffectiveCollapsed ? '10px 6px 4px' : '10px 4px 2px' }}>
            <NavLink
              to="/dashboard"
              onClick={handleLinkClick}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title={isAdmin ? 'Cuadro de Mando Integral' : 'Vista General'}
              style={isEffectiveCollapsed ? { justifyContent: 'center', padding: '10px 0', margin: '2px 6px' } : {}}
            >
              <LayoutDashboard size={18} style={{ flexShrink: 0 }} />
              {!isEffectiveCollapsed && (
                <span className="sidebar-text">
                  {isAdmin ? 'Cuadro de Mando Integral' : 'Vista General'}
                </span>
              )}
            </NavLink>
          </div>

          {/* Section title */}
          {!isEffectiveCollapsed && (
            <div className="sidebar-section-title">
              {isAdmin ? 'Módulos de Inteligencia' : 'Módulos Operativos'}
            </div>
          )}

          {/* Non-admin: flat role menu */}
          {!isAdmin && menuItems.map((item) => {
            const Icon = item.icon;
            const activeMatch = isRouteItemActive(item.path, location.pathname);
            return (
              <NavLink
                key={item.id}
                to={item.path}
                onClick={handleLinkClick}
                className={({ isActive }) => `sidebar-nav-item ${isActive || activeMatch ? 'active' : ''}`}
                title={item.label}
                style={isEffectiveCollapsed ? { justifyContent: 'center', padding: '10px 0', margin: '2px 6px' } : {}}
              >
                <Icon size={17} style={{ flexShrink: 0 }} />
                {!isEffectiveCollapsed && <span className="sidebar-text">{item.label}</span>}
              </NavLink>
            );
          })}

          {/* Admin: operative cluster groups */}
          {isAdmin && ADMIN_OPERATIVE_CLUSTERS.map((cluster) => {
            const ClusterIcon = cluster.icon;
            const isExpanded = expandedGroups[cluster.id];
            const hasActiveChild = cluster.items.some(i => isRouteItemActive(i.path, location.pathname));

            if (isEffectiveCollapsed) {
              return (
                <div key={cluster.id} style={{ padding: '2px 6px' }}>
                  <div
                    className={`sidebar-nav-item ${hasActiveChild ? 'active' : ''}`}
                    onClick={() => toggleGroup(cluster.id)}
                    title={cluster.label}
                    style={{ justifyContent: 'center', padding: '10px 0', margin: 0, cursor: 'pointer' }}
                  >
                    <ClusterIcon size={18} style={{ flexShrink: 0 }} />
                  </div>
                </div>
              );
            }

            return (
              <div key={cluster.id} className={`admin-cluster-group ${isExpanded ? 'open' : ''}`}>
                <div
                  className="admin-cluster-header"
                  onClick={() => toggleGroup(cluster.id)}
                  style={hasActiveChild ? { color: 'var(--color-ink-black)', fontWeight: 700 } : {}}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0, flex: 1 }}>
                    <ClusterIcon size={16} style={{ flexShrink: 0 }} />
                    <span className="sidebar-text">{cluster.label}</span>
                  </span>
                  {isExpanded ? (
                    <ChevronDown size={14} style={{ flexShrink: 0, marginLeft: '4px' }} />
                  ) : (
                    <ChevronRight size={14} style={{ flexShrink: 0, marginLeft: '4px' }} />
                  )}
                </div>
                {isExpanded && (
                  <div className="admin-cluster-content">
                    {cluster.items.map((item) => {
                      const ItemIcon = item.icon;
                      const activeMatch = isRouteItemActive(item.path, location.pathname);
                      return (
                        <NavLink
                          key={item.path}
                          to={item.path}
                          onClick={handleLinkClick}
                          className={({ isActive }) => `sidebar-nav-item ${isActive || activeMatch ? 'active' : ''}`}
                          title={item.label}
                        >
                          <ItemIcon size={14} style={{ flexShrink: 0 }} />
                          <span className="sidebar-text">{item.label}</span>
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ─── Ajustes Cluster / Link (Bottom-aligned inside scroll area) ─── */}
        <div style={{ marginTop: 'auto', paddingTop: '6px', borderTop: '1px solid var(--color-border)' }}>
          {isAdmin ? (
            isEffectiveCollapsed ? (
              <div style={{ padding: '2px 6px' }}>
                <div
                  className={`sidebar-nav-item ${hasAjustesActive ? 'active' : ''}`}
                  onClick={() => toggleGroup('ajustes')}
                  title="Ajustes y Gestión"
                  style={{ justifyContent: 'center', padding: '10px 0', margin: 0, cursor: 'pointer' }}
                >
                  <Settings size={18} style={{ flexShrink: 0 }} />
                </div>
              </div>
            ) : (
              <div className={`admin-cluster-group ${isAjustesExpanded ? 'open' : ''}`}>
                <div
                  className="admin-cluster-header"
                  onClick={() => toggleGroup('ajustes')}
                  style={hasAjustesActive ? { color: 'var(--color-ink-black)', fontWeight: 700 } : {}}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0, flex: 1 }}>
                    <Settings size={16} style={{ flexShrink: 0 }} />
                    <span className="sidebar-text">Ajustes</span>
                  </span>
                  {isAjustesExpanded ? (
                    <ChevronDown size={14} style={{ flexShrink: 0, marginLeft: '4px' }} />
                  ) : (
                    <ChevronRight size={14} style={{ flexShrink: 0, marginLeft: '4px' }} />
                  )}
                </div>
                {isAjustesExpanded && (
                  <div className="admin-cluster-content">
                    {AJUSTES_CLUSTER.items.map((item) => {
                      const ItemIcon = item.icon;
                      const activeMatch = isRouteItemActive(item.path, location.pathname);
                      return (
                        <NavLink
                          key={item.path}
                          to={item.path}
                          onClick={handleLinkClick}
                          className={({ isActive }) => `sidebar-nav-item ${isActive || activeMatch ? 'active' : ''}`}
                          title={item.label}
                        >
                          <ItemIcon size={14} style={{ flexShrink: 0 }} />
                          <span className="sidebar-text">{item.label}</span>
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            )
          ) : (
            <div style={{ padding: isEffectiveCollapsed ? '2px 6px' : '2px 4px' }}>
              <NavLink
                to="/ajustes"
                onClick={handleLinkClick}
                className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
                title="Ajustes del Sistema"
                style={isEffectiveCollapsed ? { justifyContent: 'center', padding: '10px 0', margin: 0 } : {}}
              >
                <SlidersHorizontal size={17} style={{ flexShrink: 0 }} />
                {!isEffectiveCollapsed && (
                  <span className="sidebar-text">
                    Ajustes
                  </span>
                )}
              </NavLink>
            </div>
          )}
        </div>
      </div>

      {/* ─── Bottom Section: Logout & DB Monitor (Compact Pinned Footer) ─── */}
      <div
        className="sidebar-bottom-section"
        style={{
          borderTop: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-fog-white)',
          paddingTop: '2px',
          flexShrink: 0,
        }}
      >
        {/* Cerrar Sesión Button */}
        <div style={{ padding: isEffectiveCollapsed ? '2px 6px 2px' : '2px 4px 2px' }}>
          <button
            onClick={handleLogoutClick}
            className="sidebar-nav-item"
            title="Cerrar sesión"
            type="button"
            style={{
              width: isEffectiveCollapsed ? '100%' : 'calc(100% - 16px)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
              color: 'var(--color-alert-red)',
              justifyContent: isEffectiveCollapsed ? 'center' : 'flex-start',
              padding: isEffectiveCollapsed ? '8px 0' : '6.5px 10px',
              margin: isEffectiveCollapsed ? 0 : '1px 8px',
            }}
          >
            <LogOut size={15} style={{ flexShrink: 0 }} />
            {!isEffectiveCollapsed && (
              <span className="sidebar-text" style={{ fontSize: '12.5px', fontWeight: 600 }}>
                Cerrar Sesión
              </span>
            )}
          </button>
        </div>

        {/* PostgreSQL status widget */}
        <div style={{ padding: isEffectiveCollapsed ? '6px 6px 8px' : '6px 14px 8px', borderTop: '1px solid var(--color-border)' }}>
          {!isEffectiveCollapsed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--color-slate-gray)', minWidth: 0 }}>
              <Activity size={13} color="var(--color-alert-green)" style={{ flexShrink: 0 }} />
              <div style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <div>PostgreSQL: <strong style={{ color: 'var(--color-alert-green)' }}>Conectado</strong></div>
                <div style={{ fontSize: '10px', color: 'var(--color-ash-gray)' }}>PoLP Enforced · JWT Secure</div>
              </div>
            </div>
          ) : (
            <Activity size={15} color="var(--color-alert-green)" style={{ margin: '0 auto', display: 'block' }} title="PostgreSQL Conectado (PoLP Enforced)" />
          )}
        </div>
      </div>
    </aside>
  );
}


