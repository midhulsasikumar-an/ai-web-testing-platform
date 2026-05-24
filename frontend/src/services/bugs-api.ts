import { apiJson, API_BASE_URL } from "@/services/http";

export interface BugApiResponse {
  bug_id: string;
  test_id?: string;
  execution_id?: string;
  user_id?: string;
  bug_name?: string;
  issue_type?: string;
  failed_step_name?: string;
  failed_step?: string;
  bug_description?: string;
  title?: string;
  description?: string;
  severity?: string;
  status?: string;
  url?: string;
  test_name?: string;
  created_at?: string;
}

export async function getAllBugs(token?: string): Promise<BugApiResponse[]> {
  console.debug("[bugs-api] GET", `${API_BASE_URL}/api/bugs`);
  return apiJson<BugApiResponse[]>("/api/bugs", {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export async function getBugById(bugId: string, token?: string): Promise<BugApiResponse> {
  console.debug("[bugs-api] GET", `${API_BASE_URL}/api/bugs/${bugId}`);
  return apiJson<BugApiResponse>(`/api/bugs/${bugId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}
