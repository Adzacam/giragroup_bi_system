import React, { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';
import NotificationPopover from './NotificationPopover';
import { notificationsApi } from '../../api/notificationsApi';

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await notificationsApi.getNotifications();
        // Handle list or NotificationListResponse
        const fetchedNotifications = res?.data || (Array.isArray(res) ? res : []);
        setNotifications(fetchedNotifications);
        setUnreadCount(fetchedNotifications.filter((n) => !n.is_read).length);
      } catch (error) {
        console.error('Failed to fetch notifications', error);
        // Fallback demo notifications
        const mockData = [
          {
            id: 1,
            title: 'Disparador de Integridad de CI',
            message: 'Inconsistencia en Cédula de Identidad en módulo POS-101. Requiere revisión.',
            severity: 'CRITICAL',
            is_read: false,
            timeAgo: 'Hace 5 min',
          },
          {
            id: 2,
            title: 'DataOps Ingesta Completada',
            message: 'Se procesaron 1,248 registros con 95.8% de tasa de limpieza.',
            severity: 'INFO',
            is_read: true,
            timeAgo: 'Hace 2 horas',
          },
        ];
        setNotifications(mockData);
        setUnreadCount(1);
      }
    };
    fetchNotifications();
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const requestBrowserPermission = async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      try {
        await Notification.requestPermission();
      } catch (err) {
        console.warn('Permiso de notificaciones omitido:', err);
      }
    }
  };

  const togglePopover = () => {
    requestBrowserPermission();
    setIsOpen((prev) => !prev);
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
    } catch (error) {
      console.error('Failed to mark all as read', error);
    } finally {
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    }
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }} ref={wrapperRef}>
      <button
        onClick={togglePopover}
        type="button"
        style={{
          position: 'relative',
          padding: '8px',
          background: 'none',
          border: 'none',
          color: 'var(--color-slate-gray)',
          cursor: 'pointer',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'color 0.2s, background-color 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = 'var(--color-ink-black)';
          e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = 'var(--color-slate-gray)';
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
        aria-label="Notificaciones"
        title="Notificaciones"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              minWidth: '17px',
              height: '17px',
              padding: '0 4px',
              borderRadius: '9999px',
              backgroundColor: 'var(--color-alert-red)',
              color: '#ffffff',
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 0 2px #ffffff',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <NotificationPopover
          notifications={notifications}
          onMarkAllRead={handleMarkAllRead}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
