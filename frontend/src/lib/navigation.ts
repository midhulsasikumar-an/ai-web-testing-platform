import {
  LayoutDashboard,
  PlayCircle,
  Bug,
  Rocket,
  History,
  Cpu,
  BarChart,
  Settings as SettingsIcon,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  description?: string;
  badge?: string;
};

export type NavSection = {
  label: string;
  items: NavItem[];
};

export const PRIMARY_NAV: NavSection[] = [
  {
    label: "Workspace",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, description: "Overview & insights" },
      { href: "/run-test", label: "Run Test", icon: PlayCircle, description: "Start a new test run" },
      { href: "/ai-workspace", label: "AI Workspace", icon: Cpu, description: "Conversational copilot" },
    ],
  },
  {
    label: "Results",
    items: [
      { href: "/test-history", label: "Test History", icon: History, description: "Past executions" },
      { href: "/bugs", label: "Bugs", icon: Bug, description: "Tracked issues" },
      { href: "/reports", label: "Reports", icon: BarChart, description: "Generated reports" },
    ],
  },
];

export const SECONDARY_NAV: NavItem[] = [
  { href: "/settings", label: "Settings", icon: SettingsIcon, description: "Workspace preferences" },
];

export const BREADCRUMB_LABELS: Record<string, string> = {
  "/": "Home",
  "/dashboard": "Dashboard",
  "/run-test": "Run Test",
  "/ai-workspace": "AI Workspace",
  "/test-history": "Test History",
  "/bugs": "Bugs",
  "/reports": "Reports",
  "/settings": "Settings",
  "/settings/profile": "Profile",
  "/settings/security": "Security",
  "/login": "Sign in",
  "/signup": "Sign up",
};

export type PageMeta = {
  title: string;
  description?: string;
  eyebrow?: string;
};

export const PAGE_META: Record<string, PageMeta> = {
  "/dashboard": {
    title: "AI Testing Command Center",
    description: "Real-time health, risk, and activity across your test runs.",
    eyebrow: "Overview",
  },
  "/run-test": {
    title: "Run Test",
    description: "Configure a new test run with AI-assisted planning.",
    eyebrow: "Execute",
  },
  "/ai-workspace": {
    title: "AI Workspace",
    description: "Conversational assistant for memory, reports, bugs, and instructions.",
    eyebrow: "Copilot",
  },
  "/test-history": {
    title: "Test History",
    description: "Browse and revisit logs from previously tested websites.",
    eyebrow: "Archive",
  },
  "/bugs": {
    title: "Bug Tracker",
    description: "Monitor bugs discovered across all tested websites and applications.",
    eyebrow: "Issues",
  },
  "/reports": {
    title: "Reports Center",
    description: "View, analyze, and download all generated legacy, AI, and multi-agent reports.",
    eyebrow: "Insights",
  },
  "/settings/profile": {
    title: "Profile",
    description: "Manage your personal information and workspace details.",
    eyebrow: "Settings",
  },
  "/settings/security": {
    title: "Security",
    description: "Authentication, password, and active session controls.",
    eyebrow: "Settings",
  },
};

export function getPageMeta(pathname: string): PageMeta {
  if (PAGE_META[pathname]) return PAGE_META[pathname];

  if (pathname.startsWith("/bugs/")) {
    return { title: "Bug Detail", description: "Inspect evidence, root cause, and remediation.", eyebrow: "Issues" };
  }
  if (pathname.startsWith("/test-history/")) {
    return { title: "Test Run Detail", description: "Inspect a specific test run.", eyebrow: "Archive" };
  }
  if (pathname.startsWith("/reports/")) {
    return { title: "Report Detail", description: "Drill into a specific report.", eyebrow: "Insights" };
  }

  const segments = pathname.split("/").filter(Boolean);
  const last = segments[segments.length - 1];
  const title = last
    ? last.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Dashboard";
  return { title, eyebrow: segments[0] || "" };
}

export function getBreadcrumbs(pathname: string): { label: string; href: string; current: boolean }[] {
  const crumbs: { label: string; href: string; current: boolean }[] = [];
  if (pathname === "/") return crumbs;

  const segments = pathname.split("/").filter(Boolean);
  let accumulated = "";
  segments.forEach((segment, index) => {
    accumulated += `/${segment}`;
    const label = BREADCRUMB_LABELS[accumulated] || segment.replace(/-/g, " ");
    crumbs.push({
      label: label.charAt(0).toUpperCase() + label.slice(1),
      href: accumulated,
      current: index === segments.length - 1,
    });
  });
  return crumbs;
}

export const ROCKET_ICON = Rocket;
