"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bell,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  HelpCircle,
  KeyRound,
  LogOut,
  Plus,
  Search,
  Settings as SettingsIcon,
  Sparkles,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";
import { useBugContext } from "@/context/bug-context";
import { getBreadcrumbs, getPageMeta, PRIMARY_NAV } from "@/lib/navigation";

interface AppHeaderProps {
  onOpenMobileNav?: () => void;
  showMobileMenuButton?: boolean;
}

const SEARCH_TARGETS = [
  ...PRIMARY_NAV.flatMap((section) => section.items),
  { href: "/settings/profile", label: "Profile", icon: User, description: "Account details" },
  { href: "/settings/security", label: "Security", icon: KeyRound, description: "Password and sessions" },
];

function getInitials(name?: string | null, fallback = "AM"): string {
  if (!name) return fallback;
  return name
    .split(" ")
    .map((segment) => segment[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function AppHeader({ onOpenMobileNav, showMobileMenuButton }: AppHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { bugs, testResults } = useBugContext();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLFormElement | null>(null);
  const notificationsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setSearchOpen(false);
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        setSearchOpen(false);
        setNotificationsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMenuOpen(false);
    setSearchOpen(false);
    setNotificationsOpen(false);
  }, [pathname]);

  const breadcrumbs = getBreadcrumbs(pathname);
  const initials = getInitials(user?.name);
  const displayName = user?.name || "Guest";
  const displayEmail = user?.email || "Not signed in";
  const roleLabel = user?.role === "admin" ? "Admin" : "Member";
  const searchResults = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return SEARCH_TARGETS.slice(0, 5);
    return SEARCH_TARGETS.filter((item) =>
      `${item.label} ${item.description ?? ""}`.toLowerCase().includes(query)
    ).slice(0, 6);
  }, [searchQuery]);
  const notifications = useMemo(() => {
    const bugItems = bugs.slice(0, 4).map((bug) => ({
      id: `bug-${bug.id}`,
      href: `/bugs/${bug.id}`,
      title: bug.title || bug.bug_name || "Detected bug",
      detail: `${bug.status} · ${bug.severity}`,
      time: bug.createdAt || "",
      type: "bug" as const,
    }));
    const testItems = testResults.slice(0, 4).map((test) => ({
      id: `test-${test.test_id}`,
      href: `/test-history/${test.test_id}`,
      title: test.test_name || test.project || test.url || "Test run",
      detail: test.outcome_label || test.overall_status || test.status || "Run update",
      time: test.created_at || test.updated_at || "",
      type: "test" as const,
    }));
    return [...bugItems, ...testItems]
      .sort((a, b) => new Date(b.time || 0).getTime() - new Date(a.time || 0).getTime())
      .slice(0, 6);
  }, [bugs, testResults]);
  const openNotificationCount = bugs.filter((bug) => bug.status === "open" || bug.status === "in-progress").length;

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    router.replace("/login");
  };

  const goTo = (href: string) => {
    setMenuOpen(false);
    setSearchOpen(false);
    setNotificationsOpen(false);
    setSearchQuery("");
    router.push(href);
  };

  const handleSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const firstResult = searchResults[0];
    if (firstResult) {
      goTo(firstResult.href);
    }
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-slate-200/80 bg-white/85 px-3 backdrop-blur-md sm:px-5",
        "supports-[backdrop-filter]:bg-white/70"
      )}
    >
      {showMobileMenuButton ? (
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition-colors hover:bg-slate-50 lg:hidden"
        >
          <span className="block h-0.5 w-4 bg-current shadow-[0_-5px_0_currentColor,0_5px_0_currentColor]" />
        </button>
      ) : null}

      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        {breadcrumbs.length > 0 ? (
          <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1 text-[12.5px] text-slate-500 md:flex">
            {breadcrumbs.map((crumb, index) => (
              <span key={crumb.href} className="flex min-w-0 items-center gap-1">
                {index > 0 ? <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" /> : null}
                {crumb.current ? (
                  <span className="truncate font-medium text-slate-900">{crumb.label}</span>
                ) : (
                  <Link
                    href={crumb.href}
                    className="truncate rounded px-1 py-0.5 transition-colors hover:text-slate-900"
                  >
                    {crumb.label}
                  </Link>
                )}
              </span>
            ))}
          </nav>
        ) : null}
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2">
        <div className="hidden md:flex items-center">
          <form ref={searchRef} className="relative block" onSubmit={handleSearchSubmit}>
            <span className="sr-only">Quick search</span>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              placeholder="Search tests, bugs, reports…"
              value={searchQuery}
              onChange={(event) => {
                setSearchQuery(event.target.value);
                setSearchOpen(true);
              }}
              onFocus={() => setSearchOpen(true)}
              className="h-8 w-56 rounded-lg border border-slate-200 bg-slate-50 pl-8 pr-3 text-[13px] text-slate-700 placeholder:text-slate-400 transition-all focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
            <span className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 items-center gap-0.5 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-500 lg:inline-flex">
              <span>⌘</span>
              <span>K</span>
            </span>
            {searchOpen ? (
              <div className="absolute right-0 top-[calc(100%+6px)] z-50 w-72 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg-token">
                {searchResults.length > 0 ? (
                  <div className="p-1">
                    {searchResults.map((item) => {
                      const Icon = item.icon;
                      return (
                        <button
                          key={item.href}
                          type="button"
                          onClick={() => goTo(item.href)}
                          className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-slate-100"
                        >
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-500">
                            <Icon className="h-3.5 w-3.5" />
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate text-[13px] font-medium text-slate-800">{item.label}</span>
                            <span className="block truncate text-[11.5px] text-slate-500">{item.description}</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <p className="px-3 py-2.5 text-[12.5px] text-slate-500">No matching destination.</p>
                )}
              </div>
            ) : null}
          </form>
        </div>

        <Link
          href={PRIMARY_NAV[0]?.items[1]?.href || "/run-test"}
          className="hidden h-8 items-center gap-1.5 rounded-lg bg-slate-900 px-3 text-[13px] font-medium text-white shadow-sm transition-all hover:bg-slate-800 active:scale-[0.98] sm:inline-flex"
        >
          <Plus className="h-3.5 w-3.5" />
          New Test
        </Link>

        <button
          type="button"
          aria-label="Ask AI"
          onClick={() => goTo("/ai-workspace")}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 text-blue-700 transition-colors hover:bg-blue-100"
          title="Ask AI"
        >
          <Sparkles className="h-3.5 w-3.5" />
        </button>

        <div className="relative" ref={notificationsRef}>
          <button
            type="button"
            aria-label="Notifications"
            aria-haspopup="menu"
            aria-expanded={notificationsOpen}
            onClick={() => setNotificationsOpen((value) => !value)}
            className={cn(
              "relative inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900",
              notificationsOpen && "bg-slate-100 text-slate-900"
            )}
          >
            <Bell className="h-4 w-4" />
            {openNotificationCount > 0 ? (
              <span className="absolute right-1 top-1 inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-blue-600 px-1 text-[9px] font-bold leading-none text-white">
                {openNotificationCount > 9 ? "9+" : openNotificationCount}
              </span>
            ) : null}
          </button>

          {notificationsOpen ? (
            <div
              role="menu"
              className="absolute right-0 top-[calc(100%+6px)] z-50 w-80 origin-top-right overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg-token"
            >
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-3 py-2.5">
                <div>
                  <p className="text-[13px] font-semibold text-slate-900">Notifications</p>
                  <p className="text-[11.5px] text-slate-500">
                    {openNotificationCount} active issue{openNotificationCount === 1 ? "" : "s"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => goTo("/bugs")}
                  className="rounded-md px-2 py-1 text-[11.5px] font-medium text-blue-700 hover:bg-blue-50"
                >
                  View bugs
                </button>
              </div>
              {notifications.length > 0 ? (
                <div className="max-h-80 overflow-y-auto p-1">
                  {notifications.map((item) => {
                    const Icon = item.type === "bug" ? AlertTriangle : item.detail.toLowerCase().includes("pass") ? CheckCircle2 : Clock;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        role="menuitem"
                        onClick={() => goTo(item.href)}
                        className="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-slate-100"
                      >
                        <span
                          className={cn(
                            "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
                            item.type === "bug" ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-700"
                          )}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-medium text-slate-800">{item.title}</span>
                          <span className="block truncate text-[11.5px] capitalize text-slate-500">{item.detail}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="px-3 py-6 text-center">
                  <CheckCircle2 className="mx-auto h-5 w-5 text-emerald-500" />
                  <p className="mt-2 text-[13px] font-medium text-slate-800">No new notifications</p>
                  <p className="mt-1 text-[11.5px] text-slate-500">Recent test and bug activity will appear here.</p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        <button
          type="button"
          aria-label="Help"
          onClick={() => goTo("/support")}
          className="hidden h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 sm:inline-flex"
        >
          <HelpCircle className="h-4 w-4" />
        </button>

        <div className="mx-1 hidden h-5 w-px bg-slate-200 sm:block" />

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((value) => !value)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className={cn(
              "flex items-center gap-2 rounded-lg px-1.5 py-1 transition-colors",
              menuOpen ? "bg-slate-100" : "hover:bg-slate-100"
            )}
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-blue-600 to-indigo-600 text-[11px] font-semibold text-white shadow-sm">
              {initials}
            </span>
            <span className="hidden text-left sm:block">
              <span className="block text-[12.5px] font-medium leading-tight text-slate-900">
                {displayName}
              </span>
              <span className="block text-[10.5px] leading-tight text-slate-500">
                {roleLabel}
              </span>
            </span>
            <ChevronDown
              className={cn(
                "hidden h-3.5 w-3.5 text-slate-400 transition-transform sm:block",
                menuOpen && "rotate-180"
              )}
            />
          </button>

          {menuOpen ? (
            <div
              role="menu"
              className="absolute right-0 top-[calc(100%+6px)] z-50 w-64 origin-top-right animate-fade-in overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg-token"
            >
              <div className="border-b border-slate-100 bg-slate-50/60 p-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-blue-600 to-indigo-600 text-[12px] font-semibold text-white">
                    {initials}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium text-slate-900">
                      {displayName}
                    </p>
                    <p className="truncate text-[11.5px] text-slate-500">
                      {displayEmail}
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-1">
                <button
                  type="button"
                  onClick={() => goTo("/settings/profile")}
                  role="menuitem"
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-slate-700 transition-colors hover:bg-slate-100"
                >
                  <User className="h-3.5 w-3.5 text-slate-500" />
                  Profile
                </button>
                <button
                  type="button"
                  onClick={() => goTo("/settings/security")}
                  role="menuitem"
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-slate-700 transition-colors hover:bg-slate-100"
                >
                  <KeyRound className="h-3.5 w-3.5 text-slate-500" />
                  Security
                </button>
                <button
                  type="button"
                  onClick={() => goTo("/settings/profile")}
                  role="menuitem"
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-slate-700 transition-colors hover:bg-slate-100"
                >
                  <SettingsIcon className="h-3.5 w-3.5 text-slate-500" />
                  Settings
                </button>
              </div>
              <div className="border-t border-slate-100 p-1">
                <button
                  type="button"
                  onClick={handleLogout}
                  role="menuitem"
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-red-600 transition-colors hover:bg-red-50"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Logout
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export function PageHeading({ className }: { className?: string }) {
  const pathname = usePathname();
  const meta = getPageMeta(pathname);
  return (
    <div className={cn("flex flex-col gap-0.5", className)}>
      {meta.eyebrow ? (
        <span className="text-eyebrow">{meta.eyebrow}</span>
      ) : null}
      <h1 className="text-h1 text-slate-900">{meta.title}</h1>
      {meta.description ? (
        <p className="text-[13px] leading-relaxed text-slate-500">{meta.description}</p>
      ) : null}
    </div>
  );
}
