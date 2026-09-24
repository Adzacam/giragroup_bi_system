import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, CheckCheck } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import { useNotifications } from '../../context/NotificationContext';
import { notificationService } from '../../services/notificationService';

export default function NotificationsPage() {
  const [filter, setFilter] = useState('ALL');
  const { notifications, unreadCount, loading, markAsRead, markAllRead } = useNotifications();

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL': return <AlertCircle size={20} color="var(--color-alert-red, #d9383a)" />;
      case 'WARNING': return <AlertTriangle size={20} color="var(--color-alert-amber, #b45309)" />;
      case 'INFO': return <Info size={20} color="#0284c7" />;
      default: return <CheckCircle2 size={20} color="var(--color-slate-gray)" />;
    }
  };

  const filteredNotifications = notificationService.filterNotifications(notifications, filter);
  const groupedNotifications = notificationService.groupByDate(filteredNotifications);

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 20px' }}>
      {/* ── Header ────────────────────────────────────────── */}
      <PageHeader
        category="SISTEMA INSTITUCIONAL"
        title="Centro de Notificaciones"
        subtitle={unreadCount > 0 ? `Tienes ${unreadCount} notificación(es) no leída(s)` : 'No tienes notificaciones pendientes'}
        action={
          unreadCount > 0 ? (
            <button 
              onClick={markAllRead}
              className="btn-pill-dark"
              type="button"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px', fontSize: '13px' }}
            >
              <CheckCheck size={16} /> Marcar todas como leídas
            </button>
          ) : null
        }
      />

      {/* ── Filters ───────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '28px', overflowX: 'auto', paddingBottom: '4px' }}>
        {[
          { key: 'ALL', label: 'Todas' },
          { key: 'CRITICAL', label: 'Críticas' },
          { key: 'WARNING', label: 'Advertencias' },
          { key: 'INFO', label: 'Informativas' },
        ].map(({ key, label }) => {
          const isActive = filter === key;
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              type="button"
              style={{
                padding: '8px 18px',
                borderRadius: '9999px',
                fontSize: '13px',
                fontWeight: 500,
                border: '1px solid var(--color-border)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                backgroundColor: isActive ? 'var(--color-ink-black)' : 'var(--color-paper-white)',
                color: isActive ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* ── Content ───────────────────────────────────────── */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--color-slate-gray)' }}>
          Cargando notificaciones...
        </div>
      ) : Object.entries(groupedNotifications).length === 0 ? (
        <div className="floating-artifact" style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--color-slate-gray)', borderRadius: 'var(--radius-cards)' }}>
          No hay notificaciones para el filtro seleccionado.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {Object.entries(groupedNotifications).map(([date, notifs]) => (
            <div key={date}>
              <h2 style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-slate-gray)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                {date}
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {notifs.map((notification) => {
                  const rawTime = notification.created_at || notification.timestamp;
                  const timeStr = rawTime ? new Date(rawTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

                  return (
                    <div 
                      key={notification.id} 
                      className="floating-artifact"
                      style={{
                        padding: '18px 20px',
                        display: 'flex',
                        gap: '16px',
                        alignItems: 'flex-start',
                        borderRadius: 'var(--radius-cards)',
                        borderLeft: !notification.is_read ? '4px solid #3b82f6' : '1px solid var(--color-border)',
                        backgroundColor: !notification.is_read ? 'rgba(251, 225, 209, 0.15)' : 'var(--color-paper-white)',
                      }}
                    >
                      <div style={{ flexShrink: 0, marginTop: '2px' }}>
                        {getSeverityIcon(notification.severity)}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '6px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <h3 style={{
                              fontSize: '15px',
                              margin: 0,
                              fontWeight: !notification.is_read ? 700 : 600,
                              color: 'var(--color-ink-black)',
                            }}>
                              {notification.title}
                            </h3>
                            {notification.category && (
                              <span style={{
                                fontSize: '11px',
                                padding: '2px 8px',
                                borderRadius: '9999px',
                                backgroundColor: 'var(--color-mist-gray)',
                                color: 'var(--color-slate-gray)',
                                fontWeight: 500,
                              }}>
                                {notification.category}
                              </span>
                            )}
                          </div>
                          {timeStr && (
                            <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontFamily: 'var(--font-mono)' }}>
                              {timeStr}
                            </span>
                          )}
                        </div>
                        <p style={{ margin: '0 0 10px 0', fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5 }}>
                          {notification.message}
                        </p>
                        {!notification.is_read && (
                          <button
                            type="button"
                            onClick={() => markAsRead(notification.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: 'var(--color-slate-gray)',
                              fontSize: '12px',
                              cursor: 'pointer',
                              padding: 0,
                              textDecoration: 'underline',
                            }}
                          >
                            Marcar como leída
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
