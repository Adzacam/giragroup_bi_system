import React from 'react';
import { useNavigate } from 'react-router-dom';

const NotificationPopover = ({ notifications, onMarkAllRead, onClose }) => {
  const navigate = useNavigate();

  const handleViewAll = () => {
    onClose();
    navigate('/notificaciones');
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-500';
      case 'WARNING': return 'bg-amber-500';
      case 'INFO': return 'bg-blue-500';
      default: return 'bg-slate-400';
    }
  };

  return (
    <div className="absolute right-0 mt-2 w-[380px] origin-top-right rounded-[24px] bg-paper-white shadow-modal ring-1 ring-black ring-opacity-5 focus:outline-none z-50 floating-artifact">
      <div className="flex items-center justify-between px-4 py-3 border-b border-mist-gray">
        <h3 className="text-lg font-bold text-ink-black serif-display">Notificaciones</h3>
        <button 
          onClick={onMarkAllRead}
          className="text-xs font-medium text-slate-gray hover:text-ink-black transition-colors"
        >
          Marcar todas como leídas
        </button>
      </div>
      
      <div className="max-h-[400px] overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-slate-gray">
            No tienes notificaciones
          </div>
        ) : (
          <ul className="divide-y divide-mist-gray">
            {notifications.map((notification) => (
              <li 
                key={notification.id} 
                className={`p-4 hover:bg-mist-gray/50 transition-colors cursor-pointer ${!notification.is_read ? 'bg-blue-50/30' : ''}`}
              >
                <div className="flex gap-3">
                  <div className="mt-1 flex-shrink-0">
                    <div className={`h-2.5 w-2.5 rounded-full ${getSeverityColor(notification.severity)}`}></div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${!notification.is_read ? 'font-bold text-ink-black' : 'font-medium text-slate-gray'}`}>
                      {notification.title}
                    </p>
                    <p className="text-sm text-slate-gray truncate mt-0.5">
                      {notification.message}
                    </p>
                    <p className="text-xs text-slate-gray mt-1 font-mono">
                      {notification.timeAgo || 'Hace un momento'}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      
      <div className="px-4 py-3 border-t border-mist-gray bg-mist-gray/20 rounded-b-[24px]">
        <button 
          onClick={handleViewAll}
          className="w-full text-center text-sm font-medium text-ink-black hover:underline"
        >
          Ver todas las notificaciones
        </button>
      </div>
    </div>
  );
};

export default NotificationPopover;
