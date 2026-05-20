// ── Test domain types ──────────────────────────────────────────────

import type { BugSeverity } from "./bug";

export type WorkflowState = 
  | "queued"
  | "running"
  | "generating_steps"
  | "executing"
  | "analyzing"
  | "completed"
  | "failed";
export interface StreamLogLine {
  time: string;
  level: "info" | "warn" | "error" | "success";
  msg: string;
}

export interface TestResult {
  id: string;
  url: string;
  status: WorkflowState;
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
