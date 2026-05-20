import { apiFetch } from "./api";
import { WorkflowState } from "@/types";

export interface ExecutionResponse {
  execution_id: string;
  status: WorkflowState;
  url?: string;
}

export const executionService = {
  startTest: (url: string, projectName: string = "Demo Project") => 
    apiFetch("/api/tests/start", {
      method: "POST",
      body: JSON.stringify({ url, project_name: projectName }),
    }) as Promise<{ data: ExecutionResponse }>,

  getExecutionStatus: (executionId: string) => 
    apiFetch(`/api/tests/${executionId}/status`, {
      method: "GET",
    }) as Promise<ExecutionResponse>,
};
