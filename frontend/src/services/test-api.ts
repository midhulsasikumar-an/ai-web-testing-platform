import { apiJson, apiFetch, API_BASE_URL } from "@/services/http";

export interface StartTestResponse {
  message: string;
  test_id: string;
  execution_id?: string;
  status: string;
}

export interface StartTestRequest {
  url: string;
  testName: string;
  goal: string;
  projectName?: string;
  testType?: string;
  aiPlan?: AIPlanResponse | null;
}

export interface AIPlanStep {
  action: string;
  target?: string | null;
  selector?: string | null;
  value?: string | null;
}

export interface AIPlanTestCase {
  title: string;
  expected?: string | null;
  steps: AIPlanStep[];
}

export interface AIPlanResponse {
  url: string;
  instruction: string;
  page_title?: string | null;
  summary: string;
  source: string;
  test_case: AIPlanTestCase;
  test_cases: AIPlanTestCase[];
  raw_plan?: Record<string, unknown> | null;
}

export interface TestApiResponse {
  test_id: string;
  url: string;
  target_url?: string;
  project: string;
  test_name?: string;
  test_type: string;
  run_type?: string;
  goal?: string;

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

  ai_report?: Record<string, unknown>;

  artifacts?: Record<string, unknown>;
  bugs?: unknown[];

  stream_logs?: Array<{
    time: string;
    level: string;
    msg: string;
    type?: string;
    details?: Record<string, unknown>;
  }>;

  ai_plan?: AIPlanResponse;

  screenshot?: {
    home?: string | null;
    button_interactions?: string[] | null;
    error?: string | null;
  };

  created_at?: string;
}

export async function startTest(
  requestOrUrl: StartTestRequest | string,
  projectName?: string,
  testType?: string,
  aiPlan?: AIPlanResponse | null
): Promise<StartTestResponse> {
  console.debug("[test-api] POST", `${API_BASE_URL}/api/tests/start`);
  const payload = typeof requestOrUrl === "string"
    ? {
        url: requestOrUrl,
        project_name: projectName,
        test_type: testType,
        ai_plan: aiPlan ?? undefined,
      }
    : {
        url: requestOrUrl.url,
        test_name: requestOrUrl.testName,
        goal: requestOrUrl.goal,
        ...(requestOrUrl.projectName ? { project_name: requestOrUrl.projectName } : {}),
        ...(requestOrUrl.testType ? { test_type: requestOrUrl.testType } : {}),
        ...(requestOrUrl.aiPlan ? { ai_plan: requestOrUrl.aiPlan } : {}),
      };

  const response = await apiFetch(`/api/tests/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function generateTestPlan(url: string, instruction: string, testType: string): Promise<AIPlanResponse> {
  console.debug("[test-api] POST", `${API_BASE_URL}/ai/plan`);
  return apiJson<AIPlanResponse>(`/ai/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, instruction, test_type: testType }),
  });
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