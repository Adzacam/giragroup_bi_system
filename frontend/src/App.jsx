import React, { Suspense, lazy, useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate, useLocation } from 'react-router-dom';
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

// DataOps (Flujo Canónico Guiado de 4 Pasos & Módulos Especializados)
const IngestView                  = lazy(() => import('./modules/dataops/IngestView'));
const PlainTextTransformationView = lazy(() => import('./modules/dataops/PlainTextTransformationView'));
const BetoReadingFlowView         = lazy(() => import('./modules/dataops/BetoReadingFlowView'));
const HumanReviewFlowView         = lazy(() => import('./modules/dataops/HumanReviewFlowView'));
const BetoNerExtractionView       = lazy(() => import('./modules/dataops/BetoNerExtractionView'));
const HumanInTheLoopView          = lazy(() => import('./modules/dataops/HumanInTheLoopView'));
const MasterDataView              = lazy(() => import('./modules/dataops/MasterDataView'));

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

/* ─── Structured Institutional Section Loading Fallback ─── */
function LoadingFallback() {
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('gira:suspense-state', { detail: { active: true } }));
    return () => {
      window.dispatchEvent(new CustomEvent('gira:suspense-state', { detail: { active: false } }));
    };
  }, []);

  return (
    <div className="section-loading-container" role="status" aria-live="polite">
      {/* Top animated progress bar inside the loading section */}
      <div className="section-loading-topbar">
        <div className="section-loading-topbar-fill" />
      </div>

      {/* Institutional Loading Banner */}
      <div className="section-loading-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              border: '3px solid var(--color-border)',
              borderTopColor: 'var(--color-gira-gold)',
              animation: 'spin 0.75s linear infinite',
              flexShrink: 0,
            }}
          />
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
              Cargando sección del sistema...
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
              Sincronizando módulo analítico y vistas operativas · GIRA Group BI
            </div>
          </div>
        </div>
        <span
          style={{
            fontSize: '10.5px',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            padding: '4px 10px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(217, 155, 38, 0.14)',
            color: 'var(--color-gira-gold)',
            whiteSpace: 'nowrap',
          }}
        >
          CARGANDO MÓDULO
        </span>
      </div>

      {/* Skeleton KPI Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
        }}
      >
        <div className="skeleton-shimmer" style={{ height: '104px' }} />
        <div className="skeleton-shimmer" style={{ height: '104px' }} />
        <div className="skeleton-shimmer" style={{ height: '104px' }} />
      </div>

      {/* Skeleton Main Content Area */}
      <div className="skeleton-shimmer" style={{ height: '280px', width: '100%' }} />
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
    AUDITOR_CALIDAD: '/dataops/ingesta',
    DIRECTOR_ACADEMICO: '/academico/rendimiento',
    ANALISTA_FINANCIERO: '/financiero/recaudacion',
  };
  return <Navigate to={redirectMap[role] || '/dashboard'} replace />;
}

/* ─── Main Layout (navbar + top loading bar + sidebar + content) ─── */
function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [topProgress, setTopProgress] = useState(0);
  const [isNavigating, setIsNavigating] = useState(false);
  const location = useLocation();
  const suspenseActiveRef = useRef(false);
  const timersRef = useRef([]);
  const lastClickTriggerRef = useRef(0);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const finishLoadingAnimation = useCallback(() => {
    clearTimers();
    setTopProgress(100);
    const tDone = setTimeout(() => {
      setIsNavigating(false);
      setTopProgress(0);
    }, 220);
    timersRef.current.push(tDone);
  }, [clearTimers]);

  const triggerLoadingAnimation = useCallback(() => {
    clearTimers();
    setIsNavigating(true);
    setTopProgress(15);

    const t1 = setTimeout(() => setTopProgress(65), 75);
    const t2 = setTimeout(() => setTopProgress(90), 190);
    const t3 = setTimeout(() => {
      if (!suspenseActiveRef.current) {
        finishLoadingAnimation();
      }
    }, 340);

    timersRef.current.push(t1, t2, t3);
  }, [clearTimers, finishLoadingAnimation]);

  // Listen for instant clicks on any internal navigation link (<a href="...">)
  useEffect(() => {
    const handleDocumentClick = (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }
      const anchor = e.target.closest ? e.target.closest('a[href]') : null;
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      if (
        !href ||
        href.startsWith('#') ||
        href.startsWith('javascript:') ||
        href.startsWith('mailto:') ||
        href.startsWith('tel:') ||
        href.startsWith('blob:') ||
        anchor.hasAttribute('download') ||
        anchor.target === '_blank'
      ) {
        return;
      }
      if (anchor.origin && anchor.origin !== window.location.origin) {
        return;
      }
      lastClickTriggerRef.current = Date.now();
      triggerLoadingAnimation();
    };

    document.addEventListener('click', handleDocumentClick, true);
    return () => document.removeEventListener('click', handleDocumentClick, true);
  }, [triggerLoadingAnimation]);

  // Trigger top loading bar on route changes (including programmatic navigate())
  useEffect(() => {
    const elapsedSinceClick = Date.now() - lastClickTriggerRef.current;
    if (elapsedSinceClick > 60 && !suspenseActiveRef.current) {
      triggerLoadingAnimation();
    }
    setIsMobileOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname, location.search, triggerLoadingAnimation]);

  // Clean up any active timers on unmount
  useEffect(() => {
    return () => clearTimers();
  }, [clearTimers]);

  // Coordinate with React Suspense lazy chunk loading
  useEffect(() => {
    const handleSuspenseState = (e) => {
      const active = Boolean(e.detail?.active);
      suspenseActiveRef.current = active;
      if (active) {
        clearTimers();
        setIsNavigating(true);
        setTopProgress(90);
      } else {
        finishLoadingAnimation();
      }
    };

    window.addEventListener('gira:suspense-state', handleSuspenseState);
    return () => window.removeEventListener('gira:suspense-state', handleSuspenseState);
  }, [clearTimers, finishLoadingAnimation]);

  // Synchronize mobile drawer & collapsed state across 960px breakpoint
  useEffect(() => {
    const media = window.matchMedia('(max-width: 960px)');
    const syncViewport = (matchesMobile) => {
      if (matchesMobile) {
        setSidebarCollapsed(false);
      } else {
        setIsMobileOpen(false);
      }
    };
    syncViewport(media.matches);

    const handleMediaChange = (e) => syncViewport(e.matches);
    media.addEventListener('change', handleMediaChange);
    return () => media.removeEventListener('change', handleMediaChange);
  }, []);

  const toggleSidebar = () => {
    if (window.matchMedia('(max-width: 960px)').matches || window.innerWidth <= 960) {
      setIsMobileOpen(prev => !prev);
    } else {
      setSidebarCollapsed(prev => !prev);
    }
  };

  return (
    <>
      {/* Fixed Viewport Top Loading Bar when clicking to change page/section */}
      <div
        id="top-navigation-loading-bar"
        className="top-navigation-loading-bar"
        aria-hidden="true"
      >
        <div
          className="top-navigation-loading-fill"
          style={{
            width: `${topProgress}%`,
            opacity: isNavigating || topProgress > 0 ? 1 : 0,
          }}
        />
      </div>

      {/* Floating Loading Section Pill Indicator */}
      {isNavigating && (
        <div className="top-loading-pill" role="status" aria-live="polite">
          <span className="top-loading-pill-spinner" />
          <span>Cargando sección...</span>
        </div>
      )}

      <div className="floating-header-container">
        <Navbar
          onToggleSidebar={toggleSidebar}
          topLoadingProgress={topProgress}
          isNavigating={isNavigating}
        />
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

      <MobileBottomNav
        onOpenMenu={() => setIsMobileOpen(prev => !prev)}
        onCloseMenu={() => setIsMobileOpen(false)}
        isMenuOpen={isMobileOpen}
      />
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
                    title: "sileo-title",
                    description: "sileo-desc",
                    badge: "sileo-badge",
                    button: "sileo-btn",
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

                {/* ─── DataOps: Flujo Canónico Guiado de 4 Pasos (AUDITOR_CALIDAD + ADMIN) ─── */}
                <Route path="dataops/ingesta" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <IngestView />
                  </RoleRoute>
                } />
                <Route path="dataops/texto" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <PlainTextTransformationView />
                  </RoleRoute>
                } />
                <Route path="dataops/lote/:id/texto" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <PlainTextTransformationView />
                  </RoleRoute>
                } />
                <Route path="dataops/beto" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <BetoReadingFlowView />
                  </RoleRoute>
                } />
                <Route path="dataops/lote/:id/beto" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <BetoReadingFlowView />
                  </RoleRoute>
                } />
                <Route path="dataops/revision" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <HumanReviewFlowView />
                  </RoleRoute>
                } />
                <Route path="dataops/lote/:id/revision" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <HumanReviewFlowView />
                  </RoleRoute>
                } />

                {/* Vistas Avanzadas y de Soporte */}
                <Route path="dataops/beto-ner" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <BetoNerExtractionView />
                  </RoleRoute>
                } />
                <Route path="dataops/auditoria-humana" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <HumanInTheLoopView />
                  </RoleRoute>
                } />
                <Route path="dataops/datos-maestros" element={
                  <RoleRoute allowedRoles={['AUDITOR_CALIDAD', 'ADMIN']}>
                    <MasterDataView />
                  </RoleRoute>
                } />

                {/* Redirecciones de Compatibilidad */}
                <Route path="dataops/nlp-lab" element={<Navigate to="/dataops/beto-ner" replace />} />
                <Route path="dataops/fuentes" element={<Navigate to="/dataops/ingesta" replace />} />
                <Route path="dataops/procesamiento" element={<Navigate to="/dataops/ingesta" replace />} />
                <Route path="dataops/entidades" element={<Navigate to="/dataops/revision" replace />} />
                <Route path="dataops/inconsistencias" element={<Navigate to="/dataops/revision" replace />} />
                <Route path="dataops/telemetria" element={<Navigate to="/dataops/beto-ner" replace />} />

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
