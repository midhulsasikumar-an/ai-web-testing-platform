"use client";

import { Bell, Search } from "lucide-react";
import { useAuth } from "@/context/auth-context";

interface HeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function Header({ title, description, children }: HeaderProps) {
  const { user } = useAuth();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((segment) => segment[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "NA";

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
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Search className="h-4 w-4" />
        </button>
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[0.6rem] font-bold text-white">
            3
          </span>
        </button>
        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 text-white text-xs font-bold">
            {initials}
          </div>
          <span className="text-sm font-medium">{user?.name || "Unknown User"}</span>
        </div>
      </div>
    </div>
  );
}
