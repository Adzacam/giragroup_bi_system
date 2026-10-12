import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, Wand2, CheckSquare,
  GitMerge, AlertTriangle, Cpu, GraduationCap, Star, BookOpen,
  TrendingUp, DollarSign, PieChart, Target, LineChart,
  Users, Settings, ChevronDown, ChevronRight, Activity, SlidersHorizontal, LogOut, X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

/* ─── Role-based menu definitions for non-admin roles ─── */
const ROLE_MENUS = {
  AUDITOR_CALIDAD: [
    { id: 'ingesta',          path: '/dataops/ingesta',          label: '① Ingesta de Archivos',       icon: FileUp },
    { id: 'revision',         path: '/dataops/revision',         label: '④ Revisión Humana (HITL)',    icon: CheckSquare },
    { id: 'datos-maestros',   path: '/dataops/datos-maestros',   label: 'Datos Maestros & Catálogo',   icon: GitMerge },
    { id: 'auditoria',        path: '/admin/auditoria',          label: 'Auditoría del Sistema',        icon: ShieldCheck },
  ],
  DIRECTOR_ACADEMICO: [
    { id: 'rendimiento',   path: '/academico/rendimiento',   label: 'Rendimiento y Alertas de Riesgo',   icon: GraduationCap },
    { id: 'docente',       path: '/academico/docente',       label: 'Evaluación y Desempeño Docente',    icon: Star },
    { id: 'catalogo',      path: '/academico/catalogo',      label: 'Catálogo Curricular y Actas',       icon: BookOpen },
    { id: 'proyeccion',    path: '/academico/proyeccion',    label: 'Proyección de Alumnos',             icon: TrendingUp },
  ],
  ANALISTA_FINANCIERO: [
    { id: 'recaudacion',   path: '/financiero/recaudacion',  label: 'Panel de Cobranzas y Recaudación',  icon: DollarSign },
    { id: 'cartera',       path: '/financiero/cartera',      label: 'Gestión de Cartera y Mora',         icon: PieChart },
    { id: 'metas',         path: '/financiero/metas',        label: 'Metas de Gestión vs. Ejecutado',    icon: Target },
    { id: 'proyeccion',    path: '/financiero/proyeccion',   label: 'Proyección Financiera',             icon: LineChart },
  ],
};

/* ─── Admin Operative clusters (Top Scrollable Section) ─── */
const ADMIN_OPERATIVE_CLUSTERS = [
  {
    id: 'dataops', label: 'Flujo DataOps & BETO', icon: ShieldCheck, defaultOpen: true,
    items: [
      { path: '/dataops/ingesta',          label: '① Ingesta de Archivos',     icon: FileUp },
      { path: '/dataops/revision',         label: '④ Revisión Humana (HITL)',  icon: CheckSquare },
      { path: '/dataops/beto-ner',         label: 'Laboratorio BETO NER',      icon: Cpu },
      { path: '/dataops/datos-maestros',   label: 'Datos Maestros & Catálogo', icon: GitMerge },
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

export default function Sidebar({ collapsed, isOpen, onClose, onToggle }) {
  const { role, logout } = useAuth();
  const location = useLocation();

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const initial = { ajustes: false };
    ADMIN_OPERATIVE_CLUSTERS.forEach(c => { initial[c.id] = c.defaultOpen; });
    return initial;
  });

  const toggleGroup = (id) => {
    if (collapsed && onToggle) {
      onToggle(); // expand on click if collapsed
    }
    setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleLinkClick = () => {
    if (onClose) onClose();
    if (window.innerWidth <= 960 && onToggle && !onClose) {
      onToggle();
    }
  };

  const isAdmin = role === 'ADMIN';
  const menuItems = !isAdmin ? (ROLE_MENUS[role] || []) : [];

  const isAjustesExpanded = expandedGroups['ajustes'];
  const hasAjustesActive = AJUSTES_CLUSTER.items.some(i => location.pathname === i.path);

  return (
    <aside
      className={`app-sidebar ${collapsed ? 'collapsed' : ''} ${isOpen ? 'open' : ''}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: 'calc(100vh - 64px)',
      }}
    >
      {/* ─── Upper Section: Main Navigation (Scrollable) ─────────── */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {/* Mobile drawer close header */}
        {isOpen && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 18px 8px', borderBottom: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.6px', color: 'var(--color-ink-black)' }}>Módulos del Sistema</span>
            <button
              onClick={onClose}
              type="button"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)', padding: '4px', display: 'flex', alignItems: 'center' }}
              title="Cerrar menú"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Dashboard link */}
        <div style={{ padding: collapsed ? '16px 8px 6px' : '16px 14px 6px' }}>
          <NavLink
            to="/dashboard"
            onClick={handleLinkClick}
            className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
            title={isAdmin ? 'Cuadro de Mando Integral' : 'Vista General'}
            style={collapsed ? { justifyContent: 'center', padding: '10px 0' } : {}}
          >
            <LayoutDashboard size={18} />
            {!collapsed && (
              <span className="sidebar-text" style={{ marginLeft: '10px' }}>
                {isAdmin ? 'Cuadro de Mando Integral' : 'Vista General'}
              </span>
            )}
          </NavLink>
        </div>

        {/* Section title */}
        {!collapsed && (
          <div className="sidebar-section-title">
            {isAdmin ? 'Módulos de Inteligencia' : 'Módulos Operativos'}
          </div>
        )}

        {/* Non-admin: flat role menu */}
        {!isAdmin && menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.id}
              to={item.path}
              onClick={handleLinkClick}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title={item.label}
              style={collapsed ? { justifyContent: 'center', padding: '10px 0' } : { padding: '10px 16px' }}
            >
              <Icon size={18} />
              {!collapsed && <span className="sidebar-text" style={{ marginLeft: '10px' }}>{item.label}</span>}
            </NavLink>
          );
        })}

        {/* Admin: operative cluster groups */}
        {isAdmin && ADMIN_OPERATIVE_CLUSTERS.map((cluster) => {
          const ClusterIcon = cluster.icon;
          const isExpanded = expandedGroups[cluster.id];
          const hasActiveChild = cluster.items.some(i => location.pathname === i.path);

          if (collapsed) {
            return (
              <div key={cluster.id} style={{ padding: '4px 8px' }}>
                <div
                  className={`sidebar-nav-item ${hasActiveChild ? 'active' : ''}`}
                  onClick={() => toggleGroup(cluster.id)}
                  title={cluster.label}
                  style={{ justifyContent: 'center', padding: '10px 0', cursor: 'pointer' }}
                >
                  <ClusterIcon size={18} />
                </div>
              </div>
            );
          }

          return (
            <div key={cluster.id} className={`admin-cluster-group ${isExpanded ? 'open' : ''}`}>
              <div
                className="admin-cluster-header"
                onClick={() => toggleGroup(cluster.id)}
                style={hasActiveChild ? { color: 'var(--color-ink-black)', fontWeight: 600 } : {}}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <ClusterIcon size={16} />
                  <span className="sidebar-text">{cluster.label}</span>
                </span>
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </div>
              {isExpanded && (
                <div className="admin-cluster-content">
                  {cluster.items.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={handleLinkClick}
                        className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
                      >
                        <ItemIcon size={14} />
                        <span className="sidebar-text" style={{ marginLeft: '8px' }}>{item.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ─── Bottom Section: Ajustes, Logout & DB Monitor (Pinned at Bottom) ─── */}
      <div
        className="sidebar-bottom-section"
        style={{
          borderTop: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-fog-white)',
          paddingTop: '6px',
          flexShrink: 0,
        }}
      >
        {/* Admin: Cluster Ajustes */}
        {isAdmin ? (
          collapsed ? (
            <div style={{ padding: '4px 8px' }}>
              <div
                className={`sidebar-nav-item ${hasAjustesActive ? 'active' : ''}`}
                onClick={() => toggleGroup('ajustes')}
                title="Ajustes y Gestión"
                style={{ justifyContent: 'center', padding: '10px 0', cursor: 'pointer' }}
              >
                <Settings size={18} />
              </div>
            </div>
          ) : (
            <div className={`admin-cluster-group ${isAjustesExpanded ? 'open' : ''}`}>
              <div
                className="admin-cluster-header"
                onClick={() => toggleGroup('ajustes')}
                style={hasAjustesActive ? { color: 'var(--color-ink-black)', fontWeight: 600 } : {}}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Settings size={16} />
                  <span className="sidebar-text">Ajustes</span>
                </span>
                {isAjustesExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </div>
              {isAjustesExpanded && (
                <div className="admin-cluster-content">
                  {AJUSTES_CLUSTER.items.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={handleLinkClick}
                        className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
                      >
                        <ItemIcon size={14} />
                        <span className="sidebar-text" style={{ marginLeft: '8px' }}>{item.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          )
        ) : (
          /* Non-admin: Direct link to Ajustes */
          <div style={{ padding: collapsed ? '4px 8px' : '4px 14px' }}>
            <NavLink
              to="/ajustes"
              onClick={handleLinkClick}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              title="Ajustes del Sistema"
              style={collapsed ? { justifyContent: 'center', padding: '10px 0' } : {}}
            >
              <SlidersHorizontal size={18} />
              {!collapsed && (
                <span className="sidebar-text" style={{ marginLeft: '10px' }}>
                  Ajustes
                </span>
              )}
            </NavLink>
          </div>
        )}

        {/* Cerrar Sesión Button */}
        <div style={{ padding: collapsed ? '2px 8px 6px' : '2px 14px 6px' }}>
          <button
            onClick={logout}
            className="sidebar-nav-item"
            title="Cerrar sesión"
            type="button"
            style={{
              width: '100%',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
              color: 'var(--color-alert-red)',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '8px 0' : '8px 12px',
            }}
          >
            <LogOut size={16} />
            {!collapsed && (
              <span className="sidebar-text" style={{ marginLeft: '10px', fontSize: '12.5px', fontWeight: 500 }}>
                Cerrar Sesión
              </span>
            )}
          </button>
        </div>

        {/* PostgreSQL status widget */}
        <div style={{ padding: collapsed ? '10px 8px 12px' : '10px 16px 14px', borderTop: '1px solid var(--color-border)' }}>
          {!collapsed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
              <Activity size={13} color="var(--color-alert-green)" />
              <div>
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
