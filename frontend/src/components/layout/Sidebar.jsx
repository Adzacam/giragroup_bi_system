import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, Wand2, CheckSquare,
  GitMerge, AlertTriangle, Cpu, GraduationCap, Star, BookOpen,
  TrendingUp, DollarSign, PieChart, Target, LineChart,
  Users, Settings, ChevronDown, ChevronRight, Activity, Menu
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

/* ─── Role-based menu definitions (matches v3/v4 HTML exactly) ─── */
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
      { path: '/dataops/fuentes',       label: 'Fase 1: Fuentes de Datos',   icon: FileUp },
      { path: '/dataops/procesamiento', label: 'Fase 2: Procesamiento',      icon: Wand2 },
      { path: '/dataops/revision',      label: 'Fase 3: Revisión Humana',    icon: CheckSquare },
      { path: '/dataops/entidades',     label: 'Entidades No Resueltas',     icon: GitMerge },
      { path: '/dataops/inconsistencias', label: 'Inconsistencias',          icon: AlertTriangle },
      { path: '/dataops/telemetria',    label: 'Telemetría IA',              icon: Cpu },
    ],
  },
  {
    id: 'acad', label: 'Área Académica', icon: GraduationCap, defaultOpen: false,
    items: [
      { path: '/academico/rendimiento', label: 'Rendimiento y Alertas',      icon: GraduationCap },
      { path: '/academico/docente',     label: 'Desempeño Docente',          icon: Star },
      { path: '/academico/catalogo',    label: 'Catálogo Curricular',        icon: BookOpen },
      { path: '/academico/proyeccion',  label: 'Proyección de Alumnos',      icon: TrendingUp },
    ],
  },
  {
    id: 'fin', label: 'Área Financiera', icon: DollarSign, defaultOpen: false,
    items: [
      { path: '/financiero/recaudacion', label: 'Recaudación',               icon: DollarSign },
      { path: '/financiero/cartera',     label: 'Cartera y Mora',            icon: PieChart },
      { path: '/financiero/metas',       label: 'Metas de Gestión',          icon: Target },
      { path: '/financiero/proyeccion',  label: 'Proyección Financiera',     icon: LineChart },
    ],
  },
  {
    id: 'admin', label: 'Administración', icon: Settings, defaultOpen: false,
    items: [
      { path: '/admin/usuarios',   label: 'Gestión de Usuarios',   icon: Users },
      { path: '/admin/catalogos',  label: 'Catálogos Maestros',    icon: Settings },
    ],
  },
];

export default function Sidebar({ collapsed, onToggle }) {
  const { role } = useAuth();
  const location = useLocation();

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const initial = {};
    ADMIN_CLUSTERS.forEach(c => { initial[c.id] = c.defaultOpen; });
    return initial;
  });

  const toggleGroup = (id) => {
    setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const isAdmin = role === 'ADMIN';
  const menuItems = !isAdmin ? (ROLE_MENUS[role] || []) : [];

  return (
    <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* ─── Top: Main dashboard link ─── */}
      <div style={{ padding: '20px 16px 8px' }}>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard size={16} />
          {!collapsed && <span className="sidebar-text">
            {isAdmin ? 'Cuadro de Mando Integral' : 'Vista General'}
          </span>}
        </NavLink>
      </div>

      {/* ─── Section title ─── */}
      {!collapsed && (
        <div className="sidebar-section-title">
          {isAdmin ? 'Administración Total' : 'Módulos'}
        </div>
      )}

      {/* ─── Non-admin: flat role menu ─── */}
      {!isAdmin && !collapsed && menuItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
            style={{ padding: '10px 20px' }}
          >
            <Icon size={16} />
            <span className="sidebar-text">{item.label}</span>
          </NavLink>
        );
      })}

      {/* ─── Admin: cluster groups ─── */}
      {isAdmin && !collapsed && ADMIN_CLUSTERS.map((cluster) => {
        const ClusterIcon = cluster.icon;
        const isExpanded = expandedGroups[cluster.id];
        const hasActiveChild = cluster.items.some(i => location.pathname === i.path);

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
                      className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
                    >
                      <ItemIcon size={14} />
                      <span className="sidebar-text">{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      {/* ─── Footer: PostgreSQL status ─── */}
      <div style={{ marginTop: 'auto', padding: '16px 20px', borderTop: '1px solid var(--color-border)' }}>
        {!collapsed ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
            <Activity size={14} color="var(--color-alert-green)" />
            <div>
              <div>PostgreSQL: <strong style={{ color: 'var(--color-alert-green)' }}>Conectado</strong></div>
              <div style={{ marginTop: '2px' }}>Latencia: 12ms · Pool: 5/10</div>
            </div>
          </div>
        ) : (
          <Activity size={16} color="var(--color-alert-green)" style={{ margin: '0 auto', display: 'block' }} />
        )}
      </div>
    </aside>
  );
}
