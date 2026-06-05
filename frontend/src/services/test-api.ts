import { apiJson, apiFetch } from "@/services/http";

export interface StartTestResponse {
  message: string;
  test_id: string;
  execution_id?: string;
  status: string;
}

export interface StartTestRequest {
  url: string;
  testName: string;
  goal?: string;
  projectName?: string;
  testType?: string;
  aiPlan?: AIPlanResponse | null;
  browser?: string;
  device?: string;
  coverageLevel?: string;
  executionSettings?: Record<string, unknown>;
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

export interface TestStepResult {
  step_index: number;
  step_name: string;
  status: "passed" | "failed" | "warning";
  error?: string | null;
  details?: string | null;
  duration_ms?: number | null;
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
    failure_category?: string | null;
    root_cause?: string | null;
    root_cause_confidence?: number | null;
    passed_steps?: number;
    failed_steps?: number;
    executed_steps?: number;
    scenario_id?: string | null;
    scenario_name?: string | null;
    step_results?: TestStepResult[];
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
  bug_lifecycle?: {
    summary?: Record<string, number> | {
      total_bugs?: number;
      by_status?: Record<string, number>;
      by_website?: Record<string, number>;
      by_workflow_stage?: Record<string, number>;
      recurring_bugs?: number;
      regressed_bugs?: number;
      records?: unknown[];
    };
    records?: Array<Record<string, unknown>>;
    top_items?: Array<{
      title: string;
      status: string;
      occurrences: number;
      regression_count: number;
      last_seen: string;
    }>;
  };

  artifacts?: Record<string, unknown>;
  bugs?: unknown[];
  resolved_bug_lifecycle?: string[];

  stream_logs?: Array<{
    time: string;
    level: string;
    msg: string;
    type?: string;
    details?: Record<string, unknown>;
  }>;

  ai_plan?: AIPlanResponse;
  screenshot_paths?: string[];

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
        ...(requestOrUrl.browser ? { browser: requestOrUrl.browser } : {}),
        ...(requestOrUrl.device ? { device: requestOrUrl.device } : {}),
        ...(requestOrUrl.coverageLevel ? { coverage_level: requestOrUrl.coverageLevel } : {}),
        ...(requestOrUrl.executionSettings ? { execution_settings: requestOrUrl.executionSettings } : {}),
      };

  const response = await apiFetch(`/api/tests/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function generateTestPlan(url: string, instruction: string, testType: string): Promise<AIPlanResponse> {
  return apiJson<AIPlanResponse>(`/ai/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, instruction, test_type: testType }),
  });
}

export async function getTestById(testId: string): Promise<TestApiResponse> {
  return apiJson<TestApiResponse>(`/api/tests/${testId}`);
}

export async function getAllTests(): Promise<TestApiResponse[]> {
  return apiJson<TestApiResponse[]>(`/api/tests`);
}
