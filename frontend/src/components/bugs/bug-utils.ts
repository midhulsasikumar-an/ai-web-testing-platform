import { BugSeverity, BugStatus } from "@/lib/types";

// ── Badge color helpers ────────────────────────────────────────────

export function severityColor(severity: BugSeverity): string {
  const map: Record<BugSeverity, string> = {
    critical: "border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400",
    high: "border-orange-500/50 text-orange-600 bg-orange-50 dark:bg-orange-950/30 dark:text-orange-400",
    medium: "border-yellow-500/50 text-yellow-700 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400",
    low: "border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400",
  };
  return map[severity];
}

export function statusColor(status: BugStatus): string {
  const map: Record<BugStatus, string> = {
    open: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
    "in-progress": "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-400",
    resolved: "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400",
    closed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return map[status];
}

// ── Date formatting ────────────────────────────────────────────────

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
