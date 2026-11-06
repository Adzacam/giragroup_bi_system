import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, Sun, Moon, Settings } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import NotificationBell from '../notifications/NotificationBell';
import UserProfileDropdown from './UserProfileDropdown';
import GiraGroupLogo from '../common/GiraLogo';

export default function Navbar({ onToggleSidebar, topLoadingProgress = 0, isNavigating = false }) {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
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
    <header className="floating-navbar">
      {/* Top Page/Section Change Loading Bar */}
      <div
        id="navbar-top-loading-bar"
        className="navbar-top-loading-bar"
        style={{
          width: `${topLoadingProgress}%`,
          opacity: isNavigating || topLoadingProgress > 0 ? 1 : 0,
        }}
      />

      {/* Brand & Toggle */}
      <div className="navbar-left-group">
        <button
          onClick={onToggleSidebar}
          className="btn-pill-ghost navbar-hamburger-btn"
          title="Abrir / Alternar menú de módulos"
          aria-label="Abrir o alternar menú lateral"
          type="button"
        >
          <Menu size={18} style={{ flexShrink: 0 }} />
        </button>

        {/* GIRAGROUP Brand SVG & Official Suite Title */}
        <div
          className="navbar-brand-trigger"
          onClick={() => navigate('/dashboard')}
        >
          <GiraGroupLogo
            size={34}
            showGroup={false}
            isGold={theme === 'dark'}
            style={{
              borderRadius: '9px',
              border: theme === 'dark' ? '1px solid #29303c' : 'none',
            }}
          />
          <div style={{ whiteSpace: 'nowrap' }}>
            <div style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '0.4px', lineHeight: 1.15, color: 'var(--color-ink-black)' }}>
              GIRA <span style={{ color: 'var(--color-gira-gold)', fontWeight: 700 }}>Group</span>
            </div>
            <div className="brand-subtext" style={{ fontSize: '9.5px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', letterSpacing: '0.9px', fontWeight: 600 }}>
              BI &amp; Intelligence System
            </div>
          </div>
        </div>
      </div>

      {/* Notifications, Theme & Profile Dropdown */}
      <div className="navbar-right-group">
        <NotificationBell />

        {/* Quick Dark/Light Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="btn-pill-ghost navbar-action-btn"
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
          type="button"
        >
          {theme === 'dark' ? <Sun size={15} color="var(--color-sienna-brown)" /> : <Moon size={15} />}
        </button>

        {/* Settings button */}
        <button
          onClick={() => navigate('/ajustes')}
          className="btn-pill-ghost navbar-action-btn navbar-settings-btn"
          title="Ajustes del Sistema"
          type="button"
        >
          <Settings size={15} />
        </button>

        {/* Interactive User Profile Dropdown */}
        <UserProfileDropdown />
      </div>

      {/* Bottom Dynamic Scroll Progress Bar (Current Section Position) */}
      <div
        id="navbar-scroll-progress-bar"
        ref={scrollBarRef}
        className="navbar-scroll-progress"
        style={{ width: '0%' }}
      />
    </header>
  );
}

