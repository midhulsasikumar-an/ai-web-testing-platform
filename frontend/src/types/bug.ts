// ── Bug domain types ───────────────────────────────────────────────

export type BugSeverity = "critical" | "high" | "medium" | "low";
export type BugStatus = "open" | "in-progress" | "resolved" | "closed";

export interface Bug {
  id: string;
  title: string;
  bug_name?: string;
  description: string;
  bug_description?: string;
  severity: BugSeverity;
  status: BugStatus;
  url: string;
  createdAt: string;
  steps: string[];
  test_id?: string;
  test_name?: string;
  assignedTo?: string;
  environment?: string;
  logs?: LogEntry[];
  evidence?: Record<string, unknown>;
}

export interface LogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "success";
  message: string;
}
