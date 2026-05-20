import { apiFetch } from "./api";
import { Bug, BugStatus } from "@/types";

export const bugsService = {
  getBugs: () => 
    apiFetch("/api/bugs", {
      method: "GET",
    }) as Promise<Bug[]>,

  updateBugStatus: (bugId: string, status: BugStatus) =>
    apiFetch(`/api/bugs/${bugId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }) as Promise<Bug>,
};
