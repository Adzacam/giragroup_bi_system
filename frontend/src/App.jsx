import React, { Suspense, lazy, useState } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { Toaster } from 'sileo';
import IsometricCanvasBackground from './components/canvas3d/IsometricCanvasBackground';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import MobileBottomNav from './components/layout/MobileBottomNav';

/* ─── Lazy-loaded modules ─── */
const LoginPage           = lazy(() => import('./modules/auth/LoginPage'));
const NotificationsPage   = lazy(() => import('./modules/notifications/NotificationsPage'));

// DataOps
const Fase1Fuentes        = lazy(() => import('./modules/dataops/Fase1Fuentes'));
const Fase2Procesamiento  = lazy(() => import('./modules/dataops/Fase2Procesamiento'));
const Fase3RevisionHumana = lazy(() => import('./modules/dataops/Fase3RevisionHumana'));
const EntidadesNoResueltas = lazy(() => import('./modules/dataops/EntidadesNoResueltas'));
const RegistroInconsistencias = lazy(() => import('./modules/dataops/RegistroInconsistencias'));
const TelemetriaIA        = lazy(() => import('./modules/dataops/TelemetriaIA'));

// Academic
const RendimientoAlertas  = lazy(() => import('./modules/academic/RendimientoAlertas'));
const DesempenoDocente    = lazy(() => import('./modules/academic/DesempenoDocente'));
const CatalogoCurricular  = lazy(() => import('./modules/academic/CatalogoCurricular'));
const ProyeccionAlumnos   = lazy(() => import('./modules/academic/ProyeccionAlumnos'));

// Finance
const RecaudacionCobranzas = lazy(() => import('./modules/finance/RecaudacionCobranzas'));
const CarteraMora         = lazy(() => import('./modules/finance/CarteraMora'));
const MetasGestion        = lazy(() => import('./modules/finance/MetasGestion'));
const ProyeccionFinanciera = lazy(() => import('./modules/finance/ProyeccionFinanciera'));

// Admin
const CuadroMandoIntegral = lazy(() => import('./modules/admin/CuadroMandoIntegral'));
const GestionUsuarios     = lazy(() => import('./modules/admin/GestionUsuarios'));
const CatalogosMaestros   = lazy(() => import('./modules/admin/CatalogosMaestros'));
const AuditoriaSistema    = lazy(() => import('./modules/admin/AuditoriaSistema'));
const AjustesSistema      = lazy(() => import('./modules/settings/AjustesSistema'));

import { ThemeProvider } from './context/ThemeContext';

/* ─── React Query Client ─── */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

/* ─── Loading spinner ─── */
function LoadingFallback() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', fontSize: '14px', color: 'var(--color-slate-gray)',
      fontFamily: 'var(--font-sohne)',
    }}>
      <div style={{ textAlign: 'center' }}>
        <div className="ambient-float-a" style={{
          width: '40px', height: '40px', borderRadius: '50%',
          border: '3px solid var(--color-border)',
          borderTopColor: 'var(--color-sienna-brown)',
          animation: 'spin 0.8s linear infinite',
          margin: '0 auto 16px',
        }} />
        Cargando módulo...
      </div>
    </div>
  );
}

/* ─── Protected Route ─── */
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

/* ─── Role-based route guard ─── */
function RoleRoute({ allowedRoles, children }) {
  const { role } = useAuth();
  if (!allowedRoles.includes(role)) return <Navigate to="/dashboard" replace />;
  return children;
}

/* ─── Default dashboard redirect by role ─── */
function DashboardRedirect() {
  const { role } = useAuth();
  const redirectMap = {
    ADMIN: '/dashboard',
    AUDITOR_CALIDAD: '/dataops/procesamiento',
    DIRECTOR_ACADEMICO: '/academico/rendimiento',
    ANALISTA_FINANCIERO: '/financiero/recaudacion',
  };
  return <Navigate to={redirectMap[role] || '/dashboard'} replace />;
}
 
/* ─── Main Layout (navbar + sidebar + content) ─── */
function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const toggleSidebar = () => {
    if (window.innerWidth <= 960) {
      setIsMobileOpen(prev => !prev);
    } else {
      setSidebarCollapsed(prev => !prev);
    }
  };

  return (
    <>
      <div className="floating-header-container">
        <Navbar onToggleSidebar={toggleSidebar} />
      </div>
      <div className="app-layout">
        {isMobileOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setIsMobileOpen(false)}
            aria-label="Cerrar menú lateral"
          />
        )}
        <Sidebar
          collapsed={sidebarCollapsed}
          isOpen={isMobileOpen}
          onClose={() => setIsMobileOpen(false)}
          onToggle={toggleSidebar}
        />
        <main className="app-content view-content-layer">
          <Suspense fallback={<LoadingFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <MobileBottomNav />
    </>
  );
}

/* ─── App ─── */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <ThemeProvider>
            <NotificationProvider>
              <Toaster
                position="top-center"
                options={{
                  fill: "#17191c",
                  roundness: 16,
                  styles: {
                    title: "text-white font-sans text-sm font-semibold",
                    description: "text-slate-300 font-sans text-xs",
                    badge: "bg-white/10",
                    button: "bg-white/15 hover:bg-white/20 text-white font-medium text-xs rounded-full px-3 py-1",
                  },
                }}
              />
              <IsometricCanvasBackground />
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                {/* Public */}
                <Route path="/login" element={<LoginPage />} />

                {/* Protected shell */}
                <Route path="/" element={
                  <ProtectedRoute>
                    <MainLayout />
                  </ProtectedRoute>
                }>
                  {/* Default redirect */}
                  <Route index element={<DashboardRedirect />} />

                  {/* Admin dashboard (also accessible to all roles as overview) */}
                  <Route path="dashboard" element={<CuadroMandoIntegral />} />

                  {/* Notifications (all roles) */}
                  <Route path="notificaciones" element={<NotificationsPage />} />

                  {/* System Settings (all roles) */}
                  <Route path="ajustes" element={<AjustesSistema />} />

                {/* ─── DataOps routes (AUDITOR_CALIDAD + ADMIN) ─── */}
                <Route path="dataops/fuentes" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <Fase1Fuentes />
                  </RoleRoute>
                } />
                <Route path="dataops/procesamiento" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <Fase2Procesamiento />
                  </RoleRoute>
                } />
                <Route path="dataops/revision" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <Fase3RevisionHumana />
                  </RoleRoute>
                } />
                <Route path="dataops/entidades" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <EntidadesNoResueltas />
                  </RoleRoute>
                } />
                <Route path="dataops/inconsistencias" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <RegistroInconsistencias />
                  </RoleRoute>
                } />
                <Route path="dataops/telemetria" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <TelemetriaIA />
                  </RoleRoute>
                } />

                {/* ─── Academic routes (DIRECTOR_ACADEMICO + ADMIN) ─── */}
                <Route path="academico/rendimiento" element={
                  <RoleRoute allowedRoles={['DIRECTOR_ACADEMICO', 'ADMIN']}>
                    <RendimientoAlertas />
                  </RoleRoute>
                } />
                <Route path="academico/docente" element={
                  <RoleRoute allowedRoles={['DIRECTOR_ACADEMICO', 'ADMIN']}>
                    <DesempenoDocente />
                  </RoleRoute>
                } />
                <Route path="academico/catalogo" element={
                  <RoleRoute allowedRoles={['DIRECTOR_ACADEMICO', 'ADMIN']}>
                    <CatalogoCurricular />
                  </RoleRoute>
                } />
                <Route path="academico/proyeccion" element={
                  <RoleRoute allowedRoles={['DIRECTOR_ACADEMICO', 'ADMIN']}>
                    <ProyeccionAlumnos />
                  </RoleRoute>
                } />

                {/* ─── Finance routes (ANALISTA_FINANCIERO + ADMIN) ─── */}
                <Route path="financiero/recaudacion" element={
                  <RoleRoute allowedRoles={['ANALISTA_FINANCIERO', 'ADMIN']}>
                    <RecaudacionCobranzas />
                  </RoleRoute>
                } />
                <Route path="financiero/cartera" element={
                  <RoleRoute allowedRoles={['ANALISTA_FINANCIERO', 'ADMIN']}>
                    <CarteraMora />
                  </RoleRoute>
                } />
                <Route path="financiero/metas" element={
                  <RoleRoute allowedRoles={['ANALISTA_FINANCIERO', 'ADMIN']}>
                    <MetasGestion />
                  </RoleRoute>
                } />
                <Route path="financiero/proyeccion" element={
                  <RoleRoute allowedRoles={['ANALISTA_FINANCIERO', 'ADMIN']}>
                    <ProyeccionFinanciera />
                  </RoleRoute>
                } />

                {/* ─── Admin & Auditoría routes ─── */}
                <Route path="admin/usuarios" element={
                  <RoleRoute allowedRoles={['ADMIN']}>
                    <GestionUsuarios />
                  </RoleRoute>
                } />
                <Route path="admin/catalogos" element={
                  <RoleRoute allowedRoles={['ADMIN']}>
                    <CatalogosMaestros />
                  </RoleRoute>
                } />
                <Route path="admin/auditoria" element={
                  <RoleRoute allowedRoles={['ADMIN', 'AUDITOR_CALIDAD']}>
                    <AuditoriaSistema />
                  </RoleRoute>
                } />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
            </NotificationProvider>
          </ThemeProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
