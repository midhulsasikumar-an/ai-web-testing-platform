const API_BASE_URL = "http://localhost:8000";

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
  const response = await fetch(`${API_BASE_URL}/api/tests/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, project_name: projectName , test_type: testType}),
  });

  if (!response.ok) {
    throw new Error(`Backend server returned ${response.status}`);
  }

  return response.json();
}

export async function getTestById(
  testId: string
): Promise<TestApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/tests/${testId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch test result`);
  }

  return response.json();
}

export async function getAllTests(): Promise<TestApiResponse[]> {
  const response = await fetch(`${API_BASE_URL}/api/tests`);

  if (!response.ok) {
    throw new Error("Failed to fetch tests");
  }

  return response.json();
}