import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, LogOut, Sun, Moon, Settings } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import NotificationBell from '../notifications/NotificationBell';

import UserProfileDropdown from './UserProfileDropdown';

export default function Navbar({ onToggleSidebar }) {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollTop;
      const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scroll = windowHeight > 0 ? (totalScroll / windowHeight) * 100 : 0;
      setScrollProgress(scroll);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className="floating-navbar">
      {/* Brand & Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <button
          onClick={onToggleSidebar}
          className="btn-pill-ghost navbar-hamburger-btn"
          style={{ padding: '7px 11px', borderRadius: '50%', cursor: 'pointer' }}
          title="Ocultar / Expandir menú"
          type="button"
        >
          <Menu size={16} />
        </button>

        {/* GIRAGROUP Brand SVG & Official Suite Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => navigate('/dashboard')}>
          <svg width="34" height="34" viewBox="0 0 100 100" fill="none" style={{ borderRadius: '9px', background: theme === 'dark' ? '#0C1E33' : '#0C1E33', padding: '4px', border: theme === 'dark' ? '1px solid #29303c' : 'none' }}>
            <path
              d="M 50 18 L 74 42 C 77 45, 77 51, 74 54 L 54 74 C 51 77, 45 77, 42 74 L 26 58 C 23 55, 23 49, 26 46 L 44 28 C 46 26, 49 26, 51 28 L 56 33 C 57 34, 57 36, 56 37 L 42 51 C 41 52, 41 54, 42 55 L 48 61 C 49 62, 51 62, 52 61 L 63 50 C 64 49, 64 47, 63 46 L 46 29"
              stroke={theme === 'dark' ? '#D99B26' : '#ffffff'}
              strokeWidth="9"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '0.4px', lineHeight: 1.15, color: 'var(--color-ink-black)' }}>
              GIRA <span style={{ color: 'var(--color-gira-gold)', fontWeight: 700 }}>Group</span>
            </div>
            <div className="brand-subtext" style={{ fontSize: '9.5px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', letterSpacing: '0.9px', fontWeight: 600 }}>
              BI &amp; DATAOPS SUITE
            </div>
          </div>
        </div>
      </div>

      {/* Notifications, Theme & Profile Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <NotificationBell />

        {/* Quick Dark/Light Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="btn-pill-ghost"
          style={{ padding: '7px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
          type="button"
        >
          {theme === 'dark' ? <Sun size={15} color="var(--color-sienna-brown)" /> : <Moon size={15} />}
        </button>

        {/* Settings button */}
        <button
          onClick={() => navigate('/ajustes')}
          className="btn-pill-ghost"
          style={{ padding: '7px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          title="Ajustes del Sistema"
          type="button"
        >
          <Settings size={15} />
        </button>

        {/* Interactive User Profile Dropdown (Obs 4 & Obs 6) */}
        <UserProfileDropdown />
      </div>

      {/* Dynamic Scroll Progress Bar */}
      <div
        id="navbar-scroll-progress-bar"
        className="navbar-scroll-progress"
        style={{ width: `${scrollProgress}%` }}
      />
    </header>
  );
}
