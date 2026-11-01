import React, { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';
import NotificationPopover from './NotificationPopover';
import { useNotifications } from '../../context/NotificationContext';

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);
  const { notifications, unreadCount, markAllRead } = useNotifications();

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
              boxShadow: '0 0 0 2px var(--color-paper-white)',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <NotificationPopover
          notifications={notifications}
          onMarkAllRead={markAllRead}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
