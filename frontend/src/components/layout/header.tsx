"use client";

import { useState, useEffect } from "react";
import { Bell, Search, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

interface HeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function Header({ title, description, children }: HeaderProps) {
  const [userName, setUserName] = useState("Alex Rivera");
  const [userInitials, setUserInitials] = useState("AR");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.name) {
          setUserName(payload.name);
          const initials = payload.name.split(' ').map((n: string) => n[0]).join('').toUpperCase();
          setUserInitials(initials);
        }
      } catch (e) {
        console.error("Failed to decode token", e);
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-2">
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            SignalTrack
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {children}
        
        {/* Search */}
        <div className="relative">
          <button 
            onClick={() => setSearchOpen(!searchOpen)}
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Search className="h-4 w-4" />
          </button>
          {searchOpen && (
            <div className="absolute right-0 mt-2 w-64 p-2 bg-card border border-border rounded-lg shadow-lg z-20">
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-primary"
                onKeyDown={(e) => e.key === "Enter" && alert(`Searching for: ${searchQuery}`)}
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button 
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[0.6rem] font-bold text-white">
              3
            </span>
          </button>
          {notificationsOpen && (
            <div className="absolute right-0 mt-2 w-64 p-2 bg-card border border-border rounded-lg shadow-lg z-20">
              <p className="text-xs font-semibold text-muted-foreground mb-2 px-2">Notifications</p>
              <div className="space-y-1">
                <div className="text-xs p-2 hover:bg-accent rounded cursor-pointer">New bug detected in auth flow.</div>
                <div className="text-xs p-2 hover:bg-accent rounded cursor-pointer">Test run #123 completed.</div>
                <div className="text-xs p-2 hover:bg-accent rounded cursor-pointer">System health at 94%.</div>
              </div>
            </div>
          )}
        </div>

        {/* Profile & Logout */}
        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 text-white text-xs font-bold">
            {userInitials}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium">{userName}</span>
            <button 
              onClick={handleLogout}
              className="text-xs text-muted-foreground hover:text-destructive text-left flex items-center gap-1"
            >
              <LogOut className="h-3 w-3" /> Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
