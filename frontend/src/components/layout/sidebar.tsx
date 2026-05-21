"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
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
  Terminal,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/auth-context";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reports", label: "Reports", icon: Terminal },
  { href: "/run-test", label: "Run Test", icon: Play },
  { href: "/test-history", label: "Test History", icon: History },
  { href: "/bugs", label: "Bugs", icon: Bug },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((segment) => segment[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "NA";

  function handleLogout() {
    logout();
    router.replace("/login");
  }

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

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {!collapsed && (
          <p className="px-3 mb-2 text-[0.65rem] font-semibold uppercase tracking-widest text-sidebar-foreground/40">
            Navigation
          </p>
        )}
        {navItems.map(({ href, label, icon: Icon }) => {
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
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-sidebar-border p-3">
        <div className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2",
          collapsed && "justify-center px-0"
        )}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 text-white text-xs font-bold">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-white truncate">{user?.name || "Unknown User"}</span>
              <span className="text-[0.65rem] text-sidebar-foreground/50 truncate">{user?.email || "No email"}</span>
            </div>
          )}
        </div>
          {!collapsed && (
            <button
              onClick={handleLogout}
              className="mt-2 w-full rounded-md border border-sidebar-border px-3 py-2 text-xs text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
            >
              Log out
            </button>
          )}
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
