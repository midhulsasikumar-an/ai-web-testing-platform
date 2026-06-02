"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Plus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";
import { PRIMARY_NAV, SECONDARY_NAV, type NavItem } from "@/lib/navigation";

function NavRow({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const pathname = usePathname();
  const active = item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group/nav relative flex items-center gap-3 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition-all duration-150",
        active
          ? "bg-blue-50 text-blue-700"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      )}
    >
      {active ? (
        <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-blue-600" />
      ) : null}
      <span
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
          active
            ? "bg-white text-blue-600 shadow-xs-token"
            : "bg-transparent text-slate-500 group-hover/nav:bg-white group-hover/nav:text-slate-700"
        )}
      >
        <Icon className="h-[15px] w-[15px]" strokeWidth={2.25} />
      </span>
      {!collapsed ? (
        <span className="flex min-w-0 flex-1 flex-col leading-tight">
          <span className="truncate">{item.label}</span>
        </span>
      ) : null}
      {!collapsed && item.badge ? (
        <span className="ml-auto inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-100 px-1.5 text-[10px] font-semibold text-blue-700">
          {item.badge}
        </span>
      ) : null}
    </Link>
  );
}

interface SidebarProps {
  onNavigate?: () => void;
  variant?: "desktop" | "mobile";
}

export function Sidebar({ onNavigate, variant = "desktop" }: SidebarProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const collapsed = false;
  const isMobile = variant === "mobile";

  const handleLogout = () => {
    logout();
    onNavigate?.();
    router.replace("/login");
  };

  return (
    <aside
      className={cn(
        "flex h-full flex-col bg-white text-slate-700",
        isMobile
          ? "w-full"
          : "hidden w-64 shrink-0 border-r border-slate-200/80 lg:flex"
      )}
    >
      {/* Brand */}
      <div className="flex h-14 items-center gap-2.5 border-b border-slate-200/80 px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 via-blue-600 to-indigo-600 text-white shadow-sm">
          <Sparkles className="h-4 w-4" />
        </div>
        {!collapsed ? (
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="text-[14px] font-semibold tracking-tight text-slate-900">
              TestPilot <span className="text-blue-600">AI</span>
            </span>
            <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-400">
              v2.0 · Pro
            </span>
          </div>
        ) : null}
      </div>

      {/* Quick action */}
      <div className="px-3 pt-3">
        <button
          type="button"
          disabled
          aria-disabled="true"
          title="Project workspaces ship in a future release. Use the AI Workspace to start new tests for now."
          className="group flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-[12.5px] font-medium text-slate-400 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          {!collapsed ? <span>New project</span> : null}
        </button>
      </div>

      {/* Primary navigation */}
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {PRIMARY_NAV.map((section) => (
          <div key={section.label} className="space-y-1">
            {!collapsed ? (
              <h3 className="px-2.5 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                {section.label}
              </h3>
            ) : null}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <div key={item.href} onClick={onNavigate}>
                  <NavRow item={item} collapsed={collapsed} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Secondary navigation */}
      <div className="border-t border-slate-200/80 px-3 py-3">
        <div className="space-y-0.5">
          {SECONDARY_NAV.map((item) => (
            <div key={item.href} onClick={onNavigate}>
              <NavRow item={item} collapsed={collapsed} />
            </div>
          ))}
        </div>
      </div>

      {/* User profile card */}
      <div className="border-t border-slate-200/80 p-3">
        <div className="flex items-center gap-2.5 rounded-lg p-2 transition-colors hover:bg-slate-50">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-slate-700 to-slate-900 text-[10.5px] font-semibold text-white">
            {(user?.name || "AM")
              .split(" ")
              .map((segment) => segment[0])
              .join("")
              .slice(0, 2)
              .toUpperCase()}
          </span>
          {!collapsed ? (
            <>
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-[12.5px] font-medium text-slate-900">
                  {user?.name || "Alex Mercer"}
                </p>
                <p className="truncate text-[11px] text-slate-500">
                  {user?.email || "Admin"}
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                aria-label="Sign out"
                className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-white hover:text-red-600"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
