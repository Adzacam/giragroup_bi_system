import React, { Suspense, useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import TareasSegundoPlano from '../../components/shared/TareasSegundoPlano';
import { useUiVersion } from '../context/UiVersionContext';
import { useSynchronizedNavigationV2 } from '../navigation/useSynchronizedNavigationV2';
import { useScrollFlowV2 } from '../transitions/useScrollFlowV2';
import SidebarV2 from './SidebarV2';
import NavbarV2 from './NavbarV2';
import MobileBottomNavV2 from './MobileBottomNavV2';
import '../styles/v2-tokens.css';
import '../styles/v2-layout.css';
import '../styles/v2-buttons.css';
import '../styles/v2-transitions.css';

function V2LoadingFallback() {
  return (
    <div className="section-loading-container" role="status" aria-live="polite">
      <div className="section-loading-topbar">
        <div className="section-loading-topbar-fill" />
      </div>
      <div className="skeleton-shimmer" style={{ height: '104px' }} />
      <div className="skeleton-shimmer" style={{ height: '280px', width: '100%' }} />
    </div>
  );
}

export default function MainLayoutV2() {
  const { role } = useAuth();
  const { fontPreset } = useUiVersion();
  const location = useLocation();
  // Sidebar oculto por defecto en V2
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const {
    navigateV2,
    prefetchOnIntent,
    isNavigating,
    topProgress,
  } = useSynchronizedNavigationV2();

  useScrollFlowV2(location.pathname);

  // Sincroniza el atributo data-ui-version="v2" en <html> solo mientras V2 está montado
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-ui-version', 'v2');
    root.setAttribute('data-v2-font', fontPreset);
    return () => {
      root.removeAttribute('data-ui-version');
      root.removeAttribute('data-v2-font');
    };
  }, [fontPreset]);

  // Cierra el sidebar en móvil al cambiar de ruta
  useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth <= 960) {
      setIsSidebarOpen(false);
    }
  }, [location.pathname]);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);

  return (
    <div
      className="v2-shell-root"
      data-ui-version="v2"
      data-v2-font={fontPreset}
      data-sidebar-open={isSidebarOpen ? 'true' : 'false'}
    >
      {isSidebarOpen && (
        <div
          className="v2-sidebar-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Cerrar menú lateral"
        />
      )}

      <SidebarV2
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        navigateV2={navigateV2}
        prefetchOnIntent={prefetchOnIntent}
      />

      <div className="v2-workspace-frame">
        <NavbarV2
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={toggleSidebar}
          navigateV2={navigateV2}
          prefetchOnIntent={prefetchOnIntent}
          topLoadingProgress={topProgress}
          isNavigating={isNavigating}
        />

        <main className="v2-main-content v2-stage" id="v2-main-content" tabIndex={-1}>
          <Suspense fallback={<V2LoadingFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      <TareasSegundoPlano role={role} />

      <MobileBottomNavV2
        onOpenMenu={toggleSidebar}
        isMenuOpen={isSidebarOpen}
        navigateV2={navigateV2}
        prefetchOnIntent={prefetchOnIntent}
      />
    </div>
  );
}
