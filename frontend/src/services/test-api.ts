import { apiJson, apiFetch, API_BASE_URL } from "@/services/http";

export interface StartTestResponse {
  message: string;
  test_id: string;
  status: string;
}

export interface TestApiResponse {
  test_id: string;
  url: string;
  project: string;
  test_type: string;

  status: string;

  overall_status?: "pass" | "warning" | "fail";

  health_score?: number;

  results: Array<{
    test: string;
    status: "pass" | "fail" | "info";
    details?: string;
  }>;

  summary?: {
    total: number;
    passed: number;
    failed: number;
    info: number;
  };

  insights?: {
    critical: string[];
    moderate: string[];
    minor: string[];
  };

  report?: string;

  recommendations?: string[];

  priority_issues?: {
    level: string;
    issue: string;
  }[];

  ai_summary?: string;

  screenshot?: {
    home?: string | null;
    button_interactions?: string[] | null;
    error?: string | null;
  };

  created_at?: string;
}

export async function startTest(
  url: string,
  projectName: string,
  testType: string
): Promise<StartTestResponse> {
  console.debug("[test-api] POST", `${API_BASE_URL}/api/tests/start`);
  const response = await apiFetch(`/api/tests/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, project_name: projectName, test_type: testType }),
  });
  return response.json();
}

export async function getTestById(
  testId: string,
  token?: string
): Promise<TestApiResponse> {
  console.debug("[test-api] GET", `${API_BASE_URL}/api/tests/${testId}`);
  return apiJson<TestApiResponse>(`/api/tests/${testId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export async function getAllTests(token?: string): Promise<TestApiResponse[]> {
  console.debug("[test-api] GET", `${API_BASE_URL}/api/tests`);
  return apiJson<TestApiResponse[]>(`/api/tests`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}