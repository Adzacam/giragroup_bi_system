import React, { useEffect, useRef } from 'react';
import { Sun, Moon, Settings } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import NotificationBell from '../../components/notifications/NotificationBell';
import UserProfileDropdown from '../../components/layout/UserProfileDropdown';
import GiraAnimatedLogoButton from '../components/GiraAnimatedLogoButton';

export default function NavbarV2({
  isSidebarOpen = false,
  onToggleSidebar,
  navigateV2,
  prefetchOnIntent,
  topLoadingProgress = 0,
  isNavigating = false,
}) {
  const { theme, toggleTheme } = useTheme();
  const scrollBarRef = useRef(null);

  useEffect(() => {
    let ticking = false;
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (scrollBarRef.current) {
            const totalScroll = document.documentElement.scrollTop;
            const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scroll = windowHeight > 0 ? (totalScroll / windowHeight) * 100 : 0;
            scrollBarRef.current.style.width = `${scroll}%`;
          }
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className="v2-topbar-sticky v2-topbar-pill" aria-label="Barra superior Augen Pro V2">
      {/* Hairlines de progreso integradas en la pastilla larga */}
      <div className="v2-topbar-progress-track" aria-hidden="true">
        <div className="v2-pill-progress-top">
          <div
            className="v2-pill-progress-top-fill"
            style={{
              width: `${topLoadingProgress}%`,
              opacity: isNavigating || topLoadingProgress > 0 ? 1 : 0,
            }}
          />
        </div>
        <div className="v2-pill-progress-bottom">
          <div ref={scrollBarRef} className="v2-pill-progress-bottom-fill" style={{ width: '0%' }} />
        </div>
      </div>

      {/* Lado izquierdo: Botón circular GIRA + Marca institucional */}
      <div className="v2-topbar-left-slot">
        {!isSidebarOpen && (
          <GiraAnimatedLogoButton
            isOpen={false}
            onClick={onToggleSidebar}
            ariaLabel="Abrir menú lateral GIRA"
            title="Abrir menú lateral GIRA"
          />
        )}
        <button
          type="button"
          className="v2-topbar-brand"
          onClick={() => navigateV2?.('/dashboard')}
          onMouseEnter={() => prefetchOnIntent?.('/dashboard')}
          title="Ir al Cuadro de Mando Integral"
        >
          <span className="v2-topbar-brand-title">
            GIRA <span className="v2-topbar-brand-gold">Group</span>
          </span>
          <span className="v2-topbar-brand-sub">BI &amp; Intelligence System</span>
        </button>
      </div>

      {/* Lado derecho: Acciones del sistema (sin links de módulos ni botón Aa) */}
      <div className="v2-actions-slot">
        <NotificationBell />

        <button
          type="button"
          onClick={toggleTheme}
          className="v2-pill-icon-btn"
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
          aria-label={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <button
          type="button"
          onClick={() => navigateV2?.('/ajustes')}
          onMouseEnter={() => prefetchOnIntent?.('/ajustes')}
          className="v2-pill-icon-btn v2-topbar-settings-btn"
          title="Ajustes del Sistema"
          aria-label="Ajustes del Sistema"
        >
          <Settings size={15} />
        </button>

        <UserProfileDropdown />
      </div>
    </header>
  );
}
