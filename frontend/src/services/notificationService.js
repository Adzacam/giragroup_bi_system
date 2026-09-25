import { notificationsApi } from '../api/notificationsApi';
import { sileoToast } from './sileoToast';

export const ROLE_NOTIFICATIONS = {
  ADMIN: {
    roleName: 'Administrador del Sistema',
    highlightMsg: '2 intentos anómalos de acceso bloqueados por política 423.',
    topLink: '/admin/auditoria',
    items: [
      {
        id: 201,
        title: 'Auditoría de Seguridad (GIRA-SEC)',
        message: '2 intentos anómalos de inicio de sesión bloqueados automáticamente por política HTTP 423.',
        severity: 'CRITICAL',
        category: 'Seguridad',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
        link: '/admin/auditoria'
      },
      {
        id: 202,
        title: 'Política Anti-Orfandad RBAC',
        message: 'Control estricto de roles: verificado mínimo de 1 administrador activo en el sistema.',
        severity: 'INFO',
        category: 'Usuarios',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
        link: '/admin/usuarios'
      },
      {
        id: 203,
        title: 'Capacidad de Almacenamiento DW',
        message: 'El clúster PostgreSQL de Data Warehouse reporta 68% de utilización de disco.',
        severity: 'WARNING',
        category: 'Infraestructura',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
        link: '/dashboard'
      }
    ]
  },
  AUDITOR_CALIDAD: {
    roleName: 'Auditor de Calidad (DataOps)',
    highlightMsg: '52 registros dudosos derivados a la bandeja de revisión humana.',
    topLink: '/dataops/revision',
    items: [
      {
        id: 301,
        title: 'Alerta de Integridad GIRA-50',
        message: '52 registros con sufijo dudoso o cédula incompleta requieren homologación manual en Fase 3.',
        severity: 'CRITICAL',
        category: 'DataOps',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
        link: '/dataops/revision'
      },
      {
        id: 302,
        title: 'Cola de Fuentes para Pipeline',
        message: 'Fuentes documentales catalogadas listas para ejecución en el pipeline de normalización.',
        severity: 'INFO',
        category: 'DataOps',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        link: '/dataops/procesamiento'
      },
      {
        id: 303,
        title: 'Clasificación Heurística Multi-Formato',
        message: 'Nuevas variantes de actas Excel y Forms catalogadas con 98.4% de confianza.',
        severity: 'SUCCESS',
        category: 'DataOps',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        link: '/dataops/fuentes'
      }
    ]
  },
  DIRECTOR_ACADEMICO: {
    roleName: 'Director Académico',
    highlightMsg: '24 estudiantes con notas ≤ 70 pts con alerta de riesgo curricular.',
    topLink: '/academic/alertas',
    items: [
      {
        id: 401,
        title: 'Alerta de Riesgo Académico',
        message: '24 estudiantes registran notas ≤ 70 pts con riesgo de deserción en POS-101.',
        severity: 'CRITICAL',
        category: 'Académico',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
        link: '/academic/alertas'
      },
      {
        id: 402,
        title: 'Proyección de Alumnos (Holt-Winters)',
        message: 'Modelo de series temporales proyecta 184 alumnos matriculados para Sep-Dic 2026.',
        severity: 'INFO',
        category: 'Académico',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
        link: '/academic/proyeccion'
      },
      {
        id: 403,
        title: 'Evaluación Docente Consolidada',
        message: 'Índice de satisfacción docente global registrado en 4.72 / 5.0 pts (Escuela de Postgrado).',
        severity: 'SUCCESS',
        category: 'Académico',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
        link: '/academic/docentes'
      }
    ]
  },
  ANALISTA_FINANCIERO: {
    roleName: 'Analista Financiero',
    highlightMsg: '42 alumnos en mora y meta mensual ejecutada en Bs. 348,290.',
    topLink: '/finance/mora',
    items: [
      {
        id: 501,
        title: 'Cartera en Mora Crítica',
        message: '42 alumnos registran cuotas impagas superiores a 60 días (saldo vencido en Bs.).',
        severity: 'CRITICAL',
        category: 'Finanzas',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
        link: '/finance/mora'
      },
      {
        id: 502,
        title: 'Recaudación Mensual Superada',
        message: 'Ejecución presupuestaria al 112.4% con Bs. 348,290 recaudados vs meta institucional.',
        severity: 'SUCCESS',
        category: 'Finanzas',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        link: '/finance/recaudacion'
      },
      {
        id: 503,
        title: 'Pronóstico de Flujo de Caja',
        message: 'Modelo OLS proyecta Bs. 412,000 en cobranzas efectivas para el siguiente trimestre.',
        severity: 'INFO',
        category: 'Finanzas',
        is_read: false,
        created_at: new Date(Date.now() - 1000 * 60 * 300).toISOString(),
        link: '/finance/proyeccion'
      }
    ]
  }
};

const DEMO_FALLBACK_NOTIFICATIONS = ROLE_NOTIFICATIONS.ADMIN.items;

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
  },

  /**
   * Obtiene la configuración de notificaciones para un rol específico y actualiza el caché.
   */
  getRoleNotifications(role) {
    const roleKey = (role || 'ADMIN').toUpperCase();
    const config = ROLE_NOTIFICATIONS[roleKey] || ROLE_NOTIFICATIONS.ADMIN;
    localStorage.setItem('gira_notifications_cache', JSON.stringify(config.items));
    return config;
  },

  /**
   * Dispara el Toast de bienvenida con notificaciones pendientes según el rol al iniciar sesión.
   */
  notifyPendingOnLogin(role, navigate) {
    const roleKey = (role || 'ADMIN').toUpperCase();
    const config = ROLE_NOTIFICATIONS[roleKey] || ROLE_NOTIFICATIONS.ADMIN;
    const pendingCount = config.items.filter(n => !n.is_read).length;

    // Actualizar caché de notificaciones activas para este rol
    localStorage.setItem('gira_notifications_cache', JSON.stringify(config.items));

    setTimeout(() => {
      sileoToast.action({
        title: `Bienvenido, ${config.roleName}`,
        description: `Tiene ${pendingCount} alertas institucionales: ${config.highlightMsg}`,
        button: {
          title: 'Ver Notificaciones',
          onClick: () => {
            if (navigate) {
              navigate(config.topLink || '/notificaciones');
            } else {
              window.location.href = '/notificaciones';
            }
          }
        }
      });
    }, 600);
  }
};
