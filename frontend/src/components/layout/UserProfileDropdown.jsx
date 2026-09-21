import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, ShieldCheck, Settings, LogOut, Sun, Moon, ChevronDown, Check } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';

export default function UserProfileDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayName = user?.name || user?.username || 'Usuario Conectado';
  const displayEmail = user?.email || (user?.username ? `${user.username}@giragroup.bo` : 'usuario@giragroup.bo');
  const displayRole = user?.role || 'ROL ACTIVO';
  const avatarInitials = (user?.name || user?.username || 'US')
    .split(' ')
    .map((p) => p[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  const handleLogout = () => {
    setIsOpen(false);
    logout();
  };

  const handleNavigate = (path) => {
    setIsOpen(false);
    navigate(path);
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }} ref={dropdownRef}>
      {/* ── Trigger Button ────────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        type="button"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'none',
          border: 'none',
          padding: '4px 8px',
          borderRadius: '9999px',
          cursor: 'pointer',
          transition: 'background-color 0.2s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)')}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        aria-label="Perfil de Usuario"
        title="Perfil de Usuario"
      >
        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)', lineHeight: 1.2 }}>
            {displayName}
          </span>
          <span style={{ fontSize: '10.5px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            {displayRole}
          </span>
        </div>

        <div style={{ position: 'relative' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              background: 'var(--color-ink-black)',
              color: 'var(--color-paper-white)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: 700,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            {avatarInitials}
          </div>
          {/* Online status indicator */}
          <span
            style={{
              position: 'absolute',
              bottom: '-1px',
              right: '-1px',
              width: '9px',
              height: '9px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-alert-green)',
              boxShadow: '0 0 0 2px var(--color-paper-white)',
            }}
          />
        </div>

        <ChevronDown size={14} style={{ color: 'var(--color-slate-gray)', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
      </button>

      {/* ── Dropdown Panel ───────────────────────────────────────── */}
      {isOpen && (
        <div
          className="floating-artifact"
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 14px)',
            width: '290px',
            backgroundColor: 'var(--color-paper-white)',
            borderRadius: '20px',
            boxShadow: 'var(--shadow-modal)',
            border: '1px solid var(--color-border)',
            zIndex: 9999,
            overflow: 'hidden',
            animation: 'modalPop 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards',
          }}
        >
          {/* Header Profile Info */}
          <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-fog-white)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '50%',
                  background: 'var(--color-ink-black)',
                  color: 'var(--color-paper-white)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '15px',
                  fontWeight: 700,
                }}
              >
                {avatarInitials}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-ink-black)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {displayName}
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {displayEmail}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: 'var(--color-mist-gray)',
                  color: 'var(--color-ink-black)',
                  letterSpacing: '0.4px',
                }}
              >
                {displayRole}
              </span>
              <span
                style={{
                  fontSize: '10px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  color: 'var(--color-alert-green)',
                  fontWeight: 500,
                }}
              >
                <ShieldCheck size={12} /> 2FA Verificado
              </span>
            </div>
          </div>

          {/* Quick Actions List */}
          <div style={{ padding: '8px' }}>
            <button
              onClick={() => handleNavigate('/ajustes')}
              type="button"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 14px',
                borderRadius: '12px',
                background: 'none',
                border: 'none',
                color: 'var(--color-ink-black)',
                fontSize: '13px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background-color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <Settings size={16} style={{ color: 'var(--color-slate-gray)' }} />
              <span>Ajustes del Sistema</span>
            </button>

            <button
              onClick={toggleTheme}
              type="button"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: '12px',
                background: 'none',
                border: 'none',
                color: 'var(--color-ink-black)',
                fontSize: '13px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background-color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {theme === 'dark' ? <Sun size={16} style={{ color: 'var(--color-sienna-brown)' }} /> : <Moon size={16} style={{ color: 'var(--color-slate-gray)' }} />}
                <span>Tema: {theme === 'dark' ? 'Modo Oscuro' : 'Modo Claro'}</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Cambiar</span>
            </button>
          </div>

          {/* Bottom Logout Button (Obs 6) */}
          <div style={{ padding: '8px', borderTop: '1px solid var(--color-border)', background: 'var(--color-fog-white)' }}>
            <button
              onClick={handleLogout}
              type="button"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: '12px',
                background: '#fee2e2',
                border: '1px solid #fca5a5',
                color: 'var(--color-alert-red)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#fecaca')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#fee2e2')}
            >
              <LogOut size={15} />
              <span>Cerrar Sesión</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
