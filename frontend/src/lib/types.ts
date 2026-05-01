// ── Core domain types ──────────────────────────────────────────────

export type BugSeverity = "critical" | "high" | "medium" | "low";
export type BugStatus = "open" | "in-progress" | "resolved" | "closed";
export type TestStatus = "passed" | "failed";

export interface Bug {
  id: string;
  title: string;
  description: string;
  severity: BugSeverity;
  status: BugStatus;
  url: string;
  createdAt: string;
  steps: string[];
  assignedTo?: string;
  environment?: string;
  logs?: LogEntry[];
}

export interface LogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "success";
  message: string;
}

export interface StreamLogLine {
  time: string;
  level: "info" | "warn" | "error" | "success";
  msg: string;
}

export interface TestResult {
  id: string;
  url: string;
  status: TestStatus;
  timestamp: string;
  duration: number; // ms
  bugId?: string;
  details: string;
  testType?: "full" | "ai" | "accessibility";
  streamLogs?: StreamLogLine[];
}

export interface AIFinding {
  id: string;
  title: string;
  description: string;
  severity: BugSeverity;
  codeSnippet?: string;
  file?: string;
  timestamp: string;
}

export interface DashboardStats {
  totalTests: number;
  passed: number;
  failed: number;
  openBugs: number;
}
