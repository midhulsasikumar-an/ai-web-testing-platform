// ── Backend API service layer ──────────────────────────────────────

const API_BASE_URL = "http://localhost:8000";

export interface TestApiResponse {
  test_id: string;
  url: string;
  project: string;
  status: string;
  results: Array<{
    test: string;
    status: "pass" | "fail";
    details?: string;
  }>;
}

/**
 * Start an automated test against a URL via the backend API.
 * Returns structured test results or throws on network/server errors.
 */
export async function startTest(
  url: string,
  projectName: string = "Demo Project"
): Promise<TestApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/tests/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, project_name: projectName }),
  });

  if (!response.ok) {
    throw new Error(`Backend server returned ${response.status}`);
  }

  const data = await response.json();
  return data.data as TestApiResponse;
}
