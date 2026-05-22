"use client";

import React, { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { collaborationApi } from '@/services/collaboration-api';
import { Notification } from '@/types/collaboration';
import { formatDistanceToNow } from 'date-fns';

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const notifs = await collaborationApi.getNotifications();
        setNotifications(notifs);
      } catch (err) {
        console.error("Failed to load notifications", err);
      }
    }
    load();
    // In a real app, you would set up SSE or polling here
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleMarkRead = async (id: string) => {
    try {
      await collaborationApi.markNotificationRead(id);
      setNotifications(notifications.map(n => n.notification_id === id ? { ...n, read: true } : n));
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await collaborationApi.markAllNotificationsRead();
      setNotifications(notifications.map(n => ({ ...n, read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setOpen(!open)}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[0.6rem] font-bold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto p-0 bg-card border border-border rounded-lg shadow-lg z-50 flex flex-col">
          <div className="flex items-center justify-between p-3 border-b border-border sticky top-0 bg-card z-10">
            <span className="text-sm font-semibold">Notifications</span>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-primary hover:underline">
                Mark all read
              </button>
            )}
          </div>
          <div className="flex flex-col divide-y divide-border">
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No notifications
              </div>
            ) : (
              notifications.map(n => (
                <div 
                  key={n.notification_id} 
                  className={`p-3 text-sm cursor-pointer hover:bg-accent/50 transition-colors ${!n.read ? 'bg-accent/20' : ''}`}
                  onClick={() => handleMarkRead(n.notification_id)}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className={`font-semibold ${!n.read ? 'text-foreground' : 'text-muted-foreground'}`}>{n.title}</span>
                    <span className="text-[0.65rem] text-muted-foreground">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground line-clamp-2">
                    {n.message}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
