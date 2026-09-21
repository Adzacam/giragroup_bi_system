import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, Wand2, CheckSquare,
  GitMerge, AlertTriangle, Cpu, GraduationCap, Star, BookOpen,
  TrendingUp, DollarSign, PieChart, Target, LineChart,
  Users, Settings, ChevronDown, ChevronRight, Activity, SlidersHorizontal, LogOut, X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

/* ─── Role-based menu definitions (matches v3/v4 HTML) ─── */
const ROLE_MENUS = {
  AUDITOR_CALIDAD: [
    { id: 'fuentes',          path: '/dataops/fuentes',          label: '1. Fuentes de Datos (Ingesta)',     icon: FileUp },
    { id: 'procesamiento',    path: '/dataops/procesamiento',    label: '2. Procesamiento & Normalización', icon: Wand2 },
    { id: 'revision',         path: '/dataops/revision',         label: '3. Bandeja de Revisión Humana',    icon: CheckSquare },
    { id: 'entidades',        path: '/dataops/entidades',        label: '4. Entidades No Resueltas',        icon: GitMerge },
    { id: 'inconsistencias',  path: '/dataops/inconsistencias',  label: '5. Registro de Inconsistencias',   icon: AlertTriangle },
    { id: 'telemetria',       path: '/dataops/telemetria',       label: '6. Telemetría y Rendimiento IA',   icon: Cpu },
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

/* ─── Admin clusters (matches HTML v4 admin navigation) ─── */
const ADMIN_CLUSTERS = [
  {
    id: 'dataops', label: 'DataOps & Procesamiento', icon: ShieldCheck, defaultOpen: true,
    items: [
      { path: '/dataops/fuentes',         label: 'Fase 1: Fuentes de Datos',   icon: FileUp },
      { path: '/dataops/procesamiento',   label: 'Fase 2: Procesamiento',      icon: Wand2 },
      { path: '/dataops/revision',        label: 'Fase 3: Revisión Humana',    icon: CheckSquare },
      { path: '/dataops/entidades',       label: 'Entidades No Resueltas',     icon: GitMerge },
      { path: '/dataops/inconsistencias', label: 'Inconsistencias',            icon: AlertTriangle },
      { path: '/dataops/telemetria',      label: 'Telemetría IA',              icon: Cpu },
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
  {
    id: 'admin', label: 'Administración', icon: Settings, defaultOpen: false,
    items: [
      { path: '/admin/usuarios',          label: 'Gestión de Usuarios',        icon: Users },
      { path: '/admin/catalogos',         label: 'Catálogos Maestros',         icon: Settings },
    ],
  },
];

export default function Sidebar({ collapsed, isOpen, onClose, onToggle }) {
  const { role, logout } = useAuth();
  const location = useLocation();

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const initial = {};
    ADMIN_CLUSTERS.forEach(c => { initial[c.id] = c.defaultOpen; });
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

  return (
    <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''} ${isOpen ? 'open' : ''}`}>
      {/* ─── Mobile drawer close header ─── */}
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
      {/* ─── Top: Main dashboard link ─── */}
      <div style={{ padding: collapsed ? '20px 8px 8px' : '20px 16px 8px' }}>
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

      {/* ─── Section title ─── */}
      {!collapsed && (
        <div className="sidebar-section-title">
          {isAdmin ? 'Administración Total' : 'Módulos Operativos'}
        </div>
      )}

      {/* ─── Non-admin: flat role menu ─── */}
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

      {/* ─── Admin: cluster groups ─── */}
      {isAdmin && ADMIN_CLUSTERS.map((cluster) => {
        const ClusterIcon = cluster.icon;
        const isExpanded = expandedGroups[cluster.id];
        const hasActiveChild = cluster.items.some(i => location.pathname === i.path);

        if (collapsed) {
          // Render only the cluster icon linking or showing tooltip
          return (
            <div key={cluster.id} style={{ padding: '6px 8px' }}>
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

      {/* ─── Settings Link (All roles) ─── */}
      <div style={{ padding: collapsed ? '8px 8px 4px' : '8px 16px 4px', marginTop: '12px' }}>
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
              Ajustes del Sistema
            </span>
          )}
        </NavLink>
      </div>

      {/* ─── Logout Link (Obs 6) ─── */}
      <div style={{ padding: collapsed ? '4px 8px 12px' : '4px 16px 12px' }}>
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
            padding: collapsed ? '10px 0' : '10px 16px',
          }}
        >
          <LogOut size={18} />
          {!collapsed && (
            <span className="sidebar-text" style={{ marginLeft: '10px' }}>
              Cerrar Sesión
            </span>
          )}
        </button>
      </div>

      {/* ─── Footer: PostgreSQL status ─── */}
      <div style={{ marginTop: 'auto', padding: collapsed ? '16px 8px' : '16px 20px', borderTop: '1px solid var(--color-border)' }}>
        {!collapsed ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
            <Activity size={14} color="var(--color-alert-green)" />
            <div>
              <div>PostgreSQL: <strong style={{ color: 'var(--color-alert-green)' }}>Conectado</strong></div>
              <div style={{ marginTop: '2px' }}>PoLP Enforced · JWT Secure</div>
            </div>
          </div>
        ) : (
          <Activity size={16} color="var(--color-alert-green)" style={{ margin: '0 auto', display: 'block' }} title="PostgreSQL Conectado (PoLP Enforced)" />
        )}
      </div>
    </aside>
  );
}
