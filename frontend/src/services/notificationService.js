import { notificationsApi } from '../api/notificationsApi';

const DEMO_FALLBACK_NOTIFICATIONS = [
  {
    id: 101,
    title: 'Alerta de Integridad de Datos',
    message: 'Inconsistencia detectada en validación de Cédula de Identidad en módulo POS-101.',
    severity: 'CRITICAL',
    category: 'DataOps',
    is_read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    link: '/dataops/revision'
  },
  {
    id: 102,
    title: 'Procesamiento de Ingesta Completo',
    message: 'El pipeline DataOps finalizó exitosamente con 95.8% de tasa de limpieza.',
    severity: 'INFO',
    category: 'DataOps',
    is_read: true,
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    link: '/dataops/procesamiento'
  },
  {
    id: 103,
    title: 'Uso de Recursos en Contenedores',
    message: 'El servicio PostgreSQL Data Warehouse reporta 82% de utilización de memoria.',
    severity: 'WARNING',
    category: 'Infraestructura',
    is_read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
    link: '/dashboard'
  }
];

export const notificationService = {
  /**
   * Obtiene la lista de notificaciones desde el backend.
   * Si la API no responde o está en modo demo/offline, usa el caché local persistido o los datos de fallback.
   */
  async fetchNotifications() {
    try {
      const res = await notificationsApi.getNotifications();
      const list = Array.isArray(res) ? res : (res?.data || []);
      if (list.length > 0) {
        localStorage.setItem('gira_notifications_cache', JSON.stringify(list));
        return list;
      }
    } catch (error) {
      console.warn('[NotificationService] Conexión API no disponible, utilizando almacenamiento local/fallback:', error.message);
    }

    const cached = localStorage.getItem('gira_notifications_cache');
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {
        console.error('[NotificationService] Error al parsear caché local de notificaciones');
      }
    }

    localStorage.setItem('gira_notifications_cache', JSON.stringify(DEMO_FALLBACK_NOTIFICATIONS));
    return DEMO_FALLBACK_NOTIFICATIONS;
  },

  /**
   * Marca una notificación individual como leída.
   */
  async markAsRead(id, currentList = []) {
    try {
      await notificationsApi.markAsRead(id);
    } catch (error) {
      console.warn('[NotificationService] Falló actualización en backend, aplicando cambio local:', error.message);
    }

    const updated = currentList.map(n => n.id === id ? { ...n, is_read: true } : n);
    localStorage.setItem('gira_notifications_cache', JSON.stringify(updated));
    return updated;
  },

  /**
   * Marca todas las notificaciones como leídas.
   */
  async markAllAsRead(currentList = []) {
    try {
      await notificationsApi.markAllRead();
    } catch (error) {
      console.warn('[NotificationService] Falló markAllRead en backend, aplicando cambio local:', error.message);
    }

    const updated = currentList.map(n => ({ ...n, is_read: true }));
    localStorage.setItem('gira_notifications_cache', JSON.stringify(updated));
    return updated;
  },

  /**
   * Emite una nueva notificación programática localmente.
   */
  createNotification({ title, message, category = 'Sistema', severity = 'INFO', link = null }, currentList = []) {
    const newNotif = {
      id: Date.now(),
      title,
      message,
      category,
      severity,
      is_read: false,
      created_at: new Date().toISOString(),
      link
    };

    const updated = [newNotif, ...currentList];
    localStorage.setItem('gira_notifications_cache', JSON.stringify(updated));
    return { newNotif, updatedList: updated };
  },

  /**
   * Calcula el total de notificaciones no leídas.
   */
  getUnreadCount(notifications = []) {
    if (!Array.isArray(notifications)) return 0;
    return notifications.filter(n => !n.is_read).length;
  },

  /**
   * Filtra las notificaciones por severidad.
   */
  filterNotifications(notifications = [], filter = 'ALL') {
    if (!Array.isArray(notifications)) return [];
    if (filter === 'ALL') return notifications;
    return notifications.filter(n => n.severity === filter);
  },

  /**
   * Agrupa las notificaciones por fecha para la vista cronológica.
   */
  groupByDate(notifications = []) {
    if (!Array.isArray(notifications)) return {};
    return notifications.reduce((acc, notif) => {
      const rawDate = notif.created_at || notif.timestamp || new Date().toISOString();
      const dateObj = new Date(rawDate);
      const dateKey = !isNaN(dateObj.getTime()) ? dateObj.toLocaleDateString() : 'Recientes';
      if (!acc[dateKey]) acc[dateKey] = [];
      acc[dateKey].push(notif);
      return acc;
    }, {});
  }
};
