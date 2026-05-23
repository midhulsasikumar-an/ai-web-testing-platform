// ── Centralized constants & color maps ─────────────────────────────

import type { BugSeverity, BugStatus } from "@/types";

// ── Log level styling ──────────────────────────────────────────────

export const LOG_LEVEL_COLORS: Record<string, string> = {
  info: "log-info",
  warn: "log-warn",
  error: "log-error",
  success: "log-success",
};

export const LOG_LEVEL_ICONS: Record<string, string> = {
  info: "ℹ",
  warn: "⚠",
  error: "✕",
  success: "✓",
};

// ── Severity styling ──────────────────────────────────────────────

export const SEVERITY_BADGE_COLORS: Record<BugSeverity, string> = {
  critical:
    "border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400",
  high: "border-orange-500/50 text-orange-600 bg-orange-50 dark:bg-orange-950/30 dark:text-orange-400",
  medium:
    "border-yellow-500/50 text-yellow-700 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400",
  low: "border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400",
};

export const SEVERITY_CHART_COLORS: Record<string, string> = {
  critical: "#ef4444",
  moderate: "#eab308",
  minor: "#3b82f6",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
};

export const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  moderate: "Moderate",
  minor: "Minor",
  high: "High",
  medium: "Medium",
  low: "Low",
};

// ── Status styling ────────────────────────────────────────────────

export const STATUS_BADGE_COLORS: Record<BugStatus, string> = {
  open: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
  "in-progress":
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-400",
  resolved:
    "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400",
  closed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

// ── Helper functions wrapping the maps ────────────────────────────

export function severityColor(severity: BugSeverity): string {
  return SEVERITY_BADGE_COLORS[severity];
}

export function statusColor(status: BugStatus): string {
  return STATUS_BADGE_COLORS[status];
}

// ── Test type config ──────────────────────────────────────────────

import { RefreshCw, ScanLine, Accessibility, CircleHelp } from "lucide-react";

export const TEST_TYPE_CONFIG: Record<
  string,
  { label: string; icon: typeof RefreshCw }
> = {
  full: { label: "Full Regression", icon: RefreshCw },
  e2e: { label: "End-to-End", icon: RefreshCw },
  ai: { label: "AI Scan", icon: ScanLine },
  accessibility: { label: "Accessibility", icon: Accessibility },
};

export const DEFAULT_TEST_TYPE_CONFIG = {
  label: "Unknown Test Type",
  icon: CircleHelp,
};

const TEST_TYPE_ALIASES: Record<string, keyof typeof TEST_TYPE_CONFIG> = {
  ai: "ai",
  "ai generated test": "ai",
  "ai-generated test": "ai",
  "ai test": "ai",
  e2e: "e2e",
  "end to end": "e2e",
  "end-to-end": "e2e",
  endtoend: "e2e",
  full: "full",
  "full regression": "full",
  regression: "full",
  "regression test": "full",
  smoke: "full",
  "smoke test": "full",
  accessibility: "accessibility",
  "accessibility test": "accessibility",
};

function normalizeTestType(testType?: string | null): string {
  return (testType ?? "").trim().toLowerCase().replace(/[_\-]+/g, " ").replace(/\s+/g, " ");
}

export function resolveTestTypeConfig(testType?: string | null) {
  const normalized = normalizeTestType(testType);

  if (normalized in TEST_TYPE_CONFIG) {
    return TEST_TYPE_CONFIG[normalized];
  }

  const alias = TEST_TYPE_ALIASES[normalized];
  if (alias && TEST_TYPE_CONFIG[alias]) {
    return TEST_TYPE_CONFIG[alias];
  }

  return DEFAULT_TEST_TYPE_CONFIG;
}
