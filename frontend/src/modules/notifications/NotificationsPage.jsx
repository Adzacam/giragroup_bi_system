import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { notificationsApi } from '../../api/notificationsApi';

const NotificationsPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('ALL');

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const data = await notificationsApi.getNotifications();
        setNotifications(data || []);
      } catch (error) {
        console.error("Failed to fetch notifications", error);
        // Mock data for demo
        setNotifications([
          { id: 1, title: "Alerta de DataOps", message: "Fallo en la extracción de datos SIGAA.", severity: "CRITICAL", category: "Sistema", is_read: false, timestamp: "2026-09-20T23:45:00Z" },
          { id: 2, title: "Procesamiento Completo", message: "El cubo de notas ha sido actualizado exitosamente.", severity: "INFO", category: "Data Warehouse", is_read: true, timestamp: "2026-09-20T10:00:00Z" },
          { id: 3, title: "Uso de CPU elevado", message: "El servidor de base de datos reporta 90% de uso.", severity: "WARNING", category: "Infraestructura", is_read: false, timestamp: "2026-09-19T14:30:00Z" }
        ]);
      }
    };
    fetchNotifications();
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (error) {
      console.error("Failed to mark all as read", error);
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL': return <AlertCircle className="text-red-500" size={20} />;
      case 'WARNING': return <AlertTriangle className="text-amber-500" size={20} />;
      case 'INFO': return <Info className="text-blue-500" size={20} />;
      default: return <CheckCircle2 className="text-slate-400" size={20} />;
    }
  };

  const filteredNotifications = filter === 'ALL' 
    ? notifications 
    : notifications.filter(n => n.severity === filter);

  const groupedNotifications = filteredNotifications.reduce((acc, notif) => {
    const date = new Date(notif.timestamp).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(notif);
    return acc;
  }, {});

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <h1 className="serif-display text-4xl text-ink-black">Centro de Notificaciones</h1>
        <button 
          onClick={handleMarkAllRead}
          className="btn-pill-dark px-6 py-2.5 text-sm whitespace-nowrap"
        >
          Marcar todas como leídas
        </button>
      </div>

      <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
        {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
              filter === f 
                ? 'bg-ink-black text-white' 
                : 'bg-mist-gray text-slate-gray hover:bg-slate-200'
            }`}
          >
            {f === 'ALL' ? 'Todas' : f === 'CRITICAL' ? 'Críticas' : f === 'WARNING' ? 'Advertencias' : 'Informativas'}
          </button>
        ))}
      </div>

      <div className="space-y-8">
        {Object.entries(groupedNotifications).length === 0 ? (
          <div className="text-center py-12 text-slate-gray bg-mist-gray/30 rounded-[24px]">
            No hay notificaciones para mostrar.
          </div>
        ) : (
          Object.entries(groupedNotifications).map(([date, notifs]) => (
            <div key={date} className="space-y-4">
              <h2 className="text-sm font-bold text-slate-gray uppercase tracking-wider">{date}</h2>
              <div className="space-y-3">
                {notifs.map((notification) => (
                  <div 
                    key={notification.id} 
                    className={`floating-artifact p-5 flex gap-4 items-start ${!notification.is_read ? 'border-l-4 border-l-blue-500' : ''}`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getSeverityIcon(notification.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className={`text-base ${!notification.is_read ? 'font-bold text-ink-black' : 'font-semibold text-slate-gray'}`}>
                          {notification.title}
                        </h3>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-mist-gray text-slate-gray font-medium">
                          {notification.category}
                        </span>
                      </div>
                      <p className="text-sm text-slate-gray mb-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-slate-400 font-mono">
                        {new Date(notification.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default NotificationsPage;
