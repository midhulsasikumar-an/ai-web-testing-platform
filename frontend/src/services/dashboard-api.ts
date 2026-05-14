const API_BASE_URL = "http://localhost:8000";

export interface AILog {
  time: string;
  level: "info" | "warn" | "error" | "success";
  msg: string;
}

export interface AISummary {
  summary: string;
  insights: string[];
  risk_level: "low" | "medium" | "high";
}

export interface RecentTest {
  test_id: string;
  project: string;
  url: string;
  overall_status: string;
  health_score: number;
  test_type: string;
  date: string;
}

export interface DashboardStatsResponse {
  total_tests: number;
  passed: number;
  failed: number;
  open_bugs: number;
  average_health: number;
  ai_summary: AISummary;
  ai_logs: AILog[];
  test_activity: {
    day: string;
    passed: number;
    failed: number;
  }[];

  bug_distribution: {
    critical: number;
    moderate: number;
    minor: number;
  };
  recent_tests: RecentTest[];
}

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/stats`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch dashboard stats");
  }

  return response.json();
}