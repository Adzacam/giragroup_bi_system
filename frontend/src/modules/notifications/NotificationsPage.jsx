import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, CheckCheck } from 'lucide-react';
import { notificationsApi } from '../../api/notificationsApi';

const NotificationsPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res = await notificationsApi.getNotifications();
      const list = Array.isArray(res) ? res : (res?.data || []);
      setNotifications(list);
    } catch (error) {
      console.error("Failed to fetch notifications", error);
      // Mock fallback data for demo
      setNotifications([
        { id: 1, title: "Alerta de Integridad de Datos", message: "Inconsistencia detectada en validación de Cédula de Identidad en módulo POS-101.", severity: "CRITICAL", category: "Sistema", is_read: false, created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
        { id: 2, title: "Procesamiento de Ingesta Completo", message: "El pipeline DataOps finalizó exitosamente con 95.8% de tasa de limpieza.", severity: "INFO", category: "DataOps", is_read: true, created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString() },
        { id: 3, title: "Uso de Recursos en Docker", message: "El servicio PostgreSQL reporta 82% de utilización de memoria.", severity: "WARNING", category: "Infraestructura", is_read: false, created_at: new Date(Date.now() - 1000 * 60 * 360).toISOString() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications(prev => (Array.isArray(prev) ? prev : []).map(n => ({ ...n, is_read: true })));
    } catch (error) {
      console.error("Failed to mark all as read", error);
      setNotifications(prev => (Array.isArray(prev) ? prev : []).map(n => ({ ...n, is_read: true })));
    }
  };

  const handleMarkAsRead = async (id) => {
    try {
      await notificationsApi.markAsRead(id);
      setNotifications(prev => (Array.isArray(prev) ? prev : []).map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (error) {
      console.error("Failed to mark as read", error);
      setNotifications(prev => (Array.isArray(prev) ? prev : []).map(n => n.id === id ? { ...n, is_read: true } : n));
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL': return <AlertCircle size={20} color="var(--color-alert-red, #d9383a)" />;
      case 'WARNING': return <AlertTriangle size={20} color="var(--color-alert-amber, #b45309)" />;
      case 'INFO': return <Info size={20} color="#0284c7" />;
      default: return <CheckCircle2 size={20} color="var(--color-slate-gray)" />;
    }
  };

  const notifsList = Array.isArray(notifications) ? notifications : [];

  const filteredNotifications = filter === 'ALL' 
    ? notifsList 
    : notifsList.filter(n => n.severity === filter);

  const groupedNotifications = filteredNotifications.reduce((acc, notif) => {
    const rawDate = notif.created_at || notif.timestamp || new Date().toISOString();
    const dateObj = new Date(rawDate);
    const date = !isNaN(dateObj.getTime()) ? dateObj.toLocaleDateString() : 'Recientes';
    if (!acc[date]) acc[date] = [];
    acc[date].push(notif);
    return acc;
  }, {});

  const unreadCount = notifsList.filter(n => !n.is_read).length;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 20px' }}>
      {/* ── Header ────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="serif-display" style={{ fontSize: '32px', margin: '0 0 6px 0', color: 'var(--color-ink-black)' }}>
            Centro de Notificaciones
          </h1>
          <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-slate-gray)' }}>
            {unreadCount > 0 ? `Tienes ${unreadCount} notificación(es) no leída(s)` : 'No tienes notificaciones pendientes'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button 
            onClick={handleMarkAllRead}
            className="btn-pill-dark"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px', fontSize: '13px' }}
          >
            <CheckCheck size={16} /> Marcar todas como leídas
          </button>
        )}
      </div>

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
                            onClick={() => handleMarkAsRead(notification.id)}
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
};

export default NotificationsPage;
