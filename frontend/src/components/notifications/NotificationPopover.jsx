import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCheck, ExternalLink, Bell } from 'lucide-react';

export default function NotificationPopover({ notifications, onMarkAllRead, onClose }) {
  const navigate = useNavigate();

  const handleViewAll = () => {
    onClose();
    navigate('/notificaciones');
  };

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: '#fee2e2', dot: '#d9383a', border: '#fca5a5' };
      case 'WARNING':
        return { bg: '#fef3c7', dot: '#b45309', border: '#fcd34d' };
      case 'INFO':
        return { bg: '#e0f2fe', dot: '#0369a1', border: '#bae6fd' };
      default:
        return { bg: '#f3f4f6', dot: '#777b86', border: '#e5e7eb' };
    }
  };

  return (
    <div
      className="floating-artifact"
      style={{
        position: 'absolute',
        right: 0,
        top: 'calc(100% + 14px)',
        width: '380px',
        backgroundColor: 'var(--color-paper-white)',
        backdropFilter: 'blur(16px)',
        borderRadius: 'var(--radius-cards)',
        boxShadow: 'var(--shadow-modal)',
        border: '1px solid var(--color-border)',
        zIndex: 9999,
        overflow: 'hidden',
        animation: 'modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      }}
    >
      {/* ── Popover Header ──────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-paper-white)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Bell size={16} style={{ color: 'var(--color-ink-black)' }} />
          <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)' }}>
            Notificaciones
          </h3>
        </div>
        <button
          onClick={onMarkAllRead}
          type="button"
          style={{
            background: 'none',
            border: 'none',
            fontSize: '12px',
            color: 'var(--color-slate-gray)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontWeight: 500,
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => (e.target.style.color = 'var(--color-ink-black)')}
          onMouseLeave={(e) => (e.target.style.color = 'var(--color-slate-gray)')}
        >
          <CheckCheck size={14} /> Marcar leídas
        </button>
      </div>

      {/* ── Notification List ───────────────────── */}
      <div style={{ maxHeight: '340px', overflowY: 'auto' }}>
        {notifications.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--color-slate-gray)', fontSize: '13.5px' }}>
            No tienes notificaciones pendientes
          </div>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {notifications.map((notification) => {
              const badge = getSeverityStyle(notification.severity);
              return (
                <li
                  key={notification.id}
                  style={{
                    padding: '14px 20px',
                    borderBottom: '1px solid rgba(236, 236, 236, 0.7)',
                    backgroundColor: !notification.is_read ? 'rgba(251, 225, 209, 0.18)' : 'transparent',
                    display: 'flex',
                    gap: '12px',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)')}
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor = !notification.is_read
                      ? 'rgba(251, 225, 209, 0.18)'
                      : 'transparent')
                  }
                  onClick={handleViewAll}
                >
                  <div style={{ marginTop: '3px', flexShrink: 0 }}>
                    <div
                      style={{
                        width: '9px',
                        height: '9px',
                        borderRadius: '50%',
                        backgroundColor: badge.dot,
                        boxShadow: `0 0 0 2px ${badge.border}`,
                      }}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: !notification.is_read ? 600 : 500,
                        color: 'var(--color-ink-black)',
                        marginBottom: '3px',
                        display: 'flex',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span>{notification.title}</span>
                      <span
                        style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '9999px',
                          backgroundColor: badge.bg,
                          color: badge.dot,
                          fontWeight: 600,
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {notification.severity}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: '12.5px',
                        color: 'var(--color-slate-gray)',
                        lineHeight: 1.4,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {notification.message}
                    </div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-ash-gray)',
                        marginTop: '4px',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {notification.timeAgo || 'Reciente'}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* ── Popover Footer ──────────────────────── */}
      <div
        style={{
          padding: '12px 20px',
          borderTop: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-fog-white)',
          textAlign: 'center',
        }}
      >
        <button
          onClick={handleViewAll}
          type="button"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-ink-black)',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
        >
          <span>Ver todas las notificaciones</span>
          <ExternalLink size={13} />
        </button>
      </div>
    </div>
  );
}
