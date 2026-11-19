import { notificationsApi } from '../api/notificationsApi';
import { sileoToast } from './sileoToast';

export const ROLE_NOTIFICATIONS = {
  ADMIN: {
    roleName: 'Administrador del Sistema / Comité Directivo',
    highlightMsg: 'Sistema seguro y políticas de integridad activas.',
    topLink: '/admin/auditoria',
    items: []
  },
  AUDITOR_CALIDAD: {
    roleName: 'Auditor de Calidad (DataOps)',
    highlightMsg: 'Monitoreo de inconsistencias de datos y pipeline activo.',
    topLink: '/dataops/revision',
    items: []
  },
  DIRECTOR_ACADEMICO: {
    roleName: 'Director Académico',
    highlightMsg: 'Monitoreo de rendimiento curricular y alertas de riesgo.',
    topLink: '/academico/alertas',
    items: []
  },
  ANALISTA_FINANCIERO: {
    roleName: 'Analista Financiero',
    highlightMsg: 'Control de recaudación y cartera de cobranzas.',
    topLink: '/financiero/recaudacion',
    items: []
  },
  ANALISTA_MARKETING: {
    roleName: 'Analista de Marketing',
    highlightMsg: 'Monitoreo de demanda y viabilidad estratégica de programas.',
    topLink: '/academico/proyeccion',
    items: []
  }
};

export const notificationService = {
  /**
   * Obtiene la lista de notificaciones desde el backend (PostgreSQL).
   */
  async fetchNotifications() {
    try {
      const res = await notificationsApi.getNotifications();
      const list = Array.isArray(res) ? res : (res?.data || []);
      localStorage.setItem('gira_notifications_cache', JSON.stringify(list));
      return list;
    } catch (error) {
      console.warn('[NotificationService] Conexión API no disponible, utilizando almacenamiento local:', error.message);
    }

    const cached = localStorage.getItem('gira_notifications_cache');
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) return parsed;
      } catch (e) {
        console.error('[NotificationService] Error al parsear caché local de notificaciones');
      }
    }

    return [];
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
   * Normaliza severidades heterogéneas del backend/caché a CRITICAL | WARNING | INFO.
   */
  normalizeSeverity(severity) {
    const raw = String(severity || 'INFO').trim().toUpperCase();
    if (['CRITICAL', 'CRITICA', 'CRÍTICA', 'ERROR', 'HIGH', 'ALTA'].includes(raw)) return 'CRITICAL';
    if (['WARNING', 'WARN', 'ADVERTENCIA', 'ALERTA', 'MEDIUM', 'MEDIA'].includes(raw)) return 'WARNING';
    return 'INFO';
  },

  /**
   * Calcula conteos por severidad normalizada para las pastillas de filtro.
   */
  getSeverityCounts(notifications = []) {
    if (!Array.isArray(notifications)) return { ALL: 0, CRITICAL: 0, WARNING: 0, INFO: 0 };
    return notifications.reduce(
      (acc, n) => {
        const sev = this.normalizeSeverity(n?.severity);
        acc.ALL += 1;
        acc[sev] = (acc[sev] || 0) + 1;
        return acc;
      },
      { ALL: 0, CRITICAL: 0, WARNING: 0, INFO: 0 }
    );
  },

  /**
   * Filtra las notificaciones por severidad normalizada.
   */
  filterNotifications(notifications = [], filter = 'ALL') {
    if (!Array.isArray(notifications)) return [];
    if (filter === 'ALL') return notifications;
    return notifications.filter((n) => this.normalizeSeverity(n?.severity) === filter);
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
  },

  /**
   * Obtiene la configuración de rol.
   */
  getRoleNotifications(role) {
    const roleKey = (role || 'ADMIN').toUpperCase();
    return ROLE_NOTIFICATIONS[roleKey] || ROLE_NOTIFICATIONS.ADMIN;
  },

  /**
   * Notifica o actualiza el progreso de una tarea sin apilar toasts por tarea_id.
   */
  notifyTaskProgress(tarea = {}) {
    const tareaId = tarea.tarea_id ?? tarea.id;
    if (!tareaId) return null;
    const estado = String(tarea.estado || 'EN_CURSO').toUpperCase();
    const type = estado === 'COMPLETADA' ? 'success' : estado === 'ERROR' ? 'error' : 'info';
    const title = tarea.title || `Tarea #${tareaId}`;
    return sileoToast.upsertTask(tareaId, {
      type,
      title,
      etapa: tarea.etapa || tarea.mensaje || tarea.stage,
      porcentaje: tarea.porcentaje,
      duration: estado === 'EN_CURSO' ? 0 : 5000,
    });
  },

  /**
   * Resume eliminaciones en bloque en un único toast ("N lotes eliminados").
   */
  notifyBulkBatchDelete(countOrIds, opts = {}) {
    const count = Array.isArray(countOrIds) ? countOrIds.length : Number(countOrIds || 0);
    if (count <= 0) return null;
    return sileoToast.bulkDeleteSummary(count, opts);
  },

  /**
   * Dispara el Toast de bienvenida con estado real al iniciar sesión.
   */
  notifyPendingOnLogin(role, navigate) {
    const roleKey = (role || 'ADMIN').toUpperCase();
    const config = ROLE_NOTIFICATIONS[roleKey] || ROLE_NOTIFICATIONS.ADMIN;

    setTimeout(() => {
      sileoToast.info({
        title: `Bienvenido, ${config.roleName}`,
        description: 'Sesión iniciada correctamente. Estado del sistema óptimo.'
      });
    }, 600);
  }
};
