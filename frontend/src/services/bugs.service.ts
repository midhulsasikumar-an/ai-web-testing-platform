import { apiFetch } from "./api";
import { Bug, BugStatus } from "@/types";

export function normalizeBug(apiBug: any): Bug {
  return {
    id: apiBug.bug_id || apiBug.id,
    title: apiBug.title,
    description: apiBug.description,
    severity: apiBug.severity,
    status: apiBug.status,
    url: apiBug.url,
    createdAt: apiBug.created_at || apiBug.createdAt || new Date().toISOString(),
    steps: apiBug.steps || [],
    assignedTo: apiBug.assigned_to_name || apiBug.assignedTo || apiBug.assignee_id,
    environment: apiBug.environment,
    logs: apiBug.logs || [],
    commentCount: apiBug.comment_count || 0,
    lastActivityAt: apiBug.last_activity_at || apiBug.updated_at,
    reviewStatus: apiBug.review_status,
  };
}

export const bugsService = {
  getBugs: async () => {
    const data = await apiFetch("/api/bugs", { method: "GET" }) as any[];
    return data.map(normalizeBug);
  },

  updateBugStatus: async (bugId: string, status: BugStatus) => {
    const data = await apiFetch(`/api/bugs/${bugId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    return normalizeBug(data);
  },
};
