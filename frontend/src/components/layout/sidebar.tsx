"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  PlayCircle,
  Bug,
  Rocket,
  History,
  Cpu,
  Workflow,
  BarChart,
  Plus,
  Settings
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/auth-context";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/run-test", label: "Run Test", icon: PlayCircle },
  { href: "/ai-workspace", label: "AI Workspace", icon: Cpu },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/test-history", label: "Test History", icon: History },
  { href: "/bugs", label: "Bugs", icon: Bug },
  { href: "/reports", label: "Reports", icon: BarChart },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const collapsed = false;

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((segment) => segment[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "AM"; // Default Alex Mercer

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <aside
      className={cn(
        "sticky top-0 h-screen flex flex-col bg-[#F8FAFC] text-slate-600 border-r border-slate-200 transition-all duration-300 ease-in-out",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* Logo / Brand */}
      <div className="flex h-16 items-center gap-3 px-6 py-8">
        <div className="text-blue-600">
          <Rocket className="h-6 w-6" />
        </div>
        {!collapsed && (
          <div className="flex flex-col min-w-0">
            <span className="text-[17px] font-bold tracking-tight text-slate-900 truncate flex items-center gap-1">
              TestPilot <span className="text-blue-600 font-bold">AI</span>
            </span>
            <span className="text-[10px] text-slate-500 truncate uppercase font-semibold">
              v2.0.0 pro
            </span>
          </div>
        )}
      </div>

      {/* New Project Button */}
      {!collapsed && (
        <div className="px-4 mb-4">
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-md py-2 text-sm font-medium transition-colors flex items-center justify-center gap-2 shadow-sm">
            <Plus className="h-4 w-4" />
            New Project
          </button>
        </div>
      )}
      {collapsed && (
        <div className="px-3 mb-4 flex justify-center">
          <button className="bg-blue-600 hover:bg-blue-700 text-white rounded-md p-2 text-sm font-medium transition-colors shadow-sm">
            <Plus className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 py-2 px-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-all duration-200",
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              )}
            >
              <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-blue-600" : "text-slate-500")} />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section (Settings & Profile) */}
      <div className="border-t border-slate-200 py-3 px-3">
         <Link
            href="/settings"
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-all duration-200 mb-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900",
              collapsed && "justify-center px-0"
            )}
          >
            <Settings className="h-[18px] w-[18px] text-slate-500 shrink-0" />
            {!collapsed && <span>Settings</span>}
          </Link>
          
        <div className={cn(
          "flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-slate-100 rounded-md transition-colors",
          collapsed && "justify-center px-0"
        )} onClick={handleLogout}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-white text-[10px] font-bold">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="text-[13px] font-medium text-slate-900 truncate">{user?.name || "Alex Mercer"}</span>
              <span className="text-[11px] text-slate-500 truncate">{user?.email || "Admin"}</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
