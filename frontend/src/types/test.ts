// ── Test domain types ──────────────────────────────────────────────

import type { BugSeverity } from "./bug";

export type TestStatus = "passed" | "failed";

export interface StreamLogLine {
  time: string;
  level: "info" | "warn" | "error" | "success";
  msg: string;
}

export interface TestResult {
  id: string;
  url: string;
  status: TestStatus;
  overall_status?: "pass" | "warning" | "fail";
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
