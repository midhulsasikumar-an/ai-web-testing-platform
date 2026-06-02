import { apiJson } from "@/services/http";

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
  evidence?: Record<string, unknown>;
}

export async function getAllBugs(): Promise<BugApiResponse[]> {
  return apiJson<BugApiResponse[]>("/api/bugs");
}

export async function getBugById(bugId: string): Promise<BugApiResponse> {
  return apiJson<BugApiResponse>(`/api/bugs/${bugId}`);
}
