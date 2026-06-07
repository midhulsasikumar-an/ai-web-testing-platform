import { apiJson } from "@/services/http";

export interface AILog {
  time: string;
  level: "info" | "warn" | "error" | "success";
  msg: string;
}

export type RiskLevel = "low" | "medium" | "high" | "unknown";

export interface AISummary {
  summary: string;
  insights: string[];
  risk_level: RiskLevel;
}

export interface RecentTest {
  test_id: string;
  test_name?: string;
  name?: string;
  project: string;
  url: string;
  overall_status: string;
  execution_status?: string;
  test_verdict?: string;
  failure_type?: string;
  outcome_label?: string;
  health_score: number;
  test_type: string;
  date: string;
}

export interface DashboardStatsResponse {
  total_tests: number;
  passed: number;
  failed: number;
  blocked: number;
  pass_rate: number;
  blocked_rate: number;
  environment_failures: number;
  target_blocked: number;
  average_duration_seconds: number;
  slowest_duration_seconds: number;
  failure_breakdown: Record<string, number>;
  open_bugs: number;
  average_health: number;
  ai_summary?: AISummary;
  ai_logs: AILog[];
  test_activity: {
    day: string;
    passed: number;
    failed: number;
    blocked?: number;
  }[];

  bug_distribution: {
    critical: number;
    moderate: number;
    minor: number;
  };
  recent_tests: RecentTest[];
}

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  return apiJson<DashboardStatsResponse>(`/api/dashboard/stats`);
}
