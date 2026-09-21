import React, { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';
import NotificationPopover from './NotificationPopover';
import { notificationsApi } from '../../api/notificationsApi';

const NotificationBell = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const data = await notificationsApi.getNotifications();
        const fetchedNotifications = data || [];
        setNotifications(fetchedNotifications);
        setUnreadCount(fetchedNotifications.filter(n => !n.is_read).length);
      } catch (error) {
        console.error("Failed to fetch notifications", error);
        // Fallback for demo
        const mockData = [
          { id: 1, title: "Alerta", message: "Fallo de extracción", severity: "CRITICAL", is_read: false, timeAgo: "5 min" }
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
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [wrapperRef]);

  const togglePopover = () => setIsOpen(!isOpen);

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all as read", error);
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    }
  };

  return (
    <div className="relative inline-block text-left" ref={wrapperRef}>
      <button
        onClick={togglePopover}
        className="relative p-2 text-slate-gray hover:text-ink-black focus:outline-none transition-colors"
        aria-label="Notifications"
      >
        <Bell size={24} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-white">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500 items-center justify-center">{unreadCount > 9 ? '9+' : unreadCount}</span>
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
};

export default NotificationBell;
