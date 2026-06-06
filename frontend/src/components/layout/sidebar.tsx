"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Play,
  Bug,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  History,
  LogOut,
  User,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/auth-context";
import { SystemStatus } from "@/components/dashboard/system-status";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/run-test", label: "Run Test", icon: Play },
  { href: "/test-history", label: "History", icon: History },
  { href: "/bugs", label: "Bugs", icon: Bug },
];

const bottomNavItems = [
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/profile", label: "Profile", icon: User },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();

  const initials = user
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const renderNavLink = (
    { href, label, icon: Icon }: (typeof navItems)[0],
  ) => {
    const active =
      href === "/" ? pathname === "/" : pathname.startsWith(href);
    return (
      <Link
        key={href}
        href={href}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
          active
            ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-sidebar-primary/25"
            : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        )}
      >
        <Icon className="h-[18px] w-[18px] shrink-0" />
        {!collapsed && <span>{label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        "sticky top-0 h-screen flex flex-col bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out",
        collapsed ? "w-[68px]" : "w-[250px]"
      )}
    >
      {/* Logo / Brand */}
      <div className="flex h-16 items-center gap-3 px-4 border-b border-sidebar-border">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground">
          <Zap className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-bold tracking-tight text-white truncate">
              SignalTrack
            </span>
            <span className="text-[0.65rem] text-sidebar-foreground/60 truncate">
              Precision QA System
            </span>
          </div>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {!collapsed && (
          <p className="px-3 mb-2 text-[0.65rem] font-semibold uppercase tracking-widest text-sidebar-foreground/40">
            Main
          </p>
        )}
        {navItems.map(renderNavLink)}

        {/* Separator + Bottom Nav */}
        <div className="pt-4 mt-4 border-t border-sidebar-border/50 space-y-1">
          {!collapsed && (
            <p className="px-3 mb-2 text-[0.65rem] font-semibold uppercase tracking-widest text-sidebar-foreground/40">
              Account
            </p>
          )}
          {bottomNavItems.map(renderNavLink)}
        </div>
      </nav>

      {/* System Status */}
      <div className="px-3 pb-1">
        <SystemStatus collapsed={collapsed} />
      </div>

      {/* User section */}
      <div className="border-t border-sidebar-border p-3">
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2",
            collapsed && "justify-center px-0"
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 text-white text-xs font-bold">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-semibold text-white truncate">
                {user?.name || "User"}
              </span>
              <span className="text-[0.65rem] text-sidebar-foreground/50 truncate">
                {user?.email || ""}
              </span>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={logout}
              className="p-1.5 rounded-md text-sidebar-foreground/40 hover:text-red-400 hover:bg-sidebar-accent transition-all duration-200"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center h-10 border-t border-sidebar-border text-sidebar-foreground/50 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-all duration-200"
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </button>
    </aside>
  );
}
