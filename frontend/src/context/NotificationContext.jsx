import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { notificationService } from '../services/notificationService';
import { sileoToast } from '../services/sileoToast';

const NotificationContext = createContext({
  notifications: [],
  unreadCount: 0,
  loading: false,
  markAsRead: async () => {},
  markAllRead: async () => {},
  refreshNotifications: async () => {},
  notify: () => {},
});

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const refreshNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const list = await notificationService.fetchNotifications();
      setNotifications(list);
    } catch (e) {
      console.error('[NotificationContext] Error cargando notificaciones:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshNotifications();
  }, [refreshNotifications]);

  const markAsRead = useCallback(async (id) => {
    setNotifications((prev) => {
      const updated = prev.map((n) => (n.id === id ? { ...n, is_read: true } : n));
      notificationService.markAsRead(id, prev);
      return updated;
    });
  }, []);

  const markAllRead = useCallback(async () => {
    setNotifications((prev) => {
      const updated = prev.map((n) => ({ ...n, is_read: true }));
      notificationService.markAllAsRead(prev);
      return updated;
    });
  }, []);

  const notify = useCallback(({ title, message, category = 'Sistema', severity = 'INFO', link = null }) => {
    const sev = (severity || 'INFO').toUpperCase();
    if (sev === 'CRITICAL' || sev === 'ERROR') {
      sileoToast.error({ title, description: message, position: 'top-center' });
    } else if (sev === 'WARNING') {
      sileoToast.warning({ title, description: message, position: 'top-center' });
    } else if (sev === 'SUCCESS') {
      sileoToast.success({ title, description: message, position: 'top-center' });
    } else {
      sileoToast.info({ title, description: message, position: 'top-center' });
    }

    setNotifications((prev) => {
      const { updatedList } = notificationService.createNotification(
        { title, message, category, severity, link },
        prev
      );

      // Si el navegador tiene permisos de notificación nativa, despacharla también
      if ('Notification' in window && Notification.permission === 'granted') {
        try {
          new Notification(`[GIRAGROUP] ${title}`, {
            body: message,
            icon: '/favicon.ico',
          });
        } catch (e) {
          // Ignore desktop notification error in environments without full support
        }
      }

      return updatedList;
    });
  }, []);

  const unreadCount = notificationService.getUnreadCount(notifications);

  const value = {
    notifications,
    unreadCount,
    loading,
    markAsRead,
    markAllRead,
    refreshNotifications,
    notify,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications debe utilizarse dentro de un NotificationProvider');
  }
  return context;
}
