import { apiFetch, apiJson } from "@/services/http";

export type AIWorkspaceContext = {
  website?: string | null;
  workflow?: string | null;
  report?: string | null;
  test_run_id?: string | null;
  bug_id?: string | null;
  screenshot_path?: string | null;
};

export type AIChatSession = {
  session_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  active_context?: AIWorkspaceContext;
};

export type AIChatMessage = {
  session_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  retrieved_data?: unknown[];
  ai_summary?: string | null;
};

export type AIMemory = {
  memory_id: string;
  user_id: string;
  memory_type: string;
  content: string;
  importance: number;
  created_at: string;
  updated_at?: string;
};

export type AIChatResponse = {
  session_id: string;
  response: string;
  intent: string;
  retrieved_count: number;
  retrieved_data?: unknown[];
  assistant_payload?: Record<string, unknown>;
};

export type AIInstructionResponse = {
  topic: string;
  instructions: string;
};

export type AIAnalysisResponse = Record<string, unknown>;

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiJson<T>(path, init, { auth: true });
}

export async function listChatSessions(): Promise<AIChatSession[]> {
  const data = await requestJson<{ items: AIChatSession[] }>("/api/ai-workspace/sessions");
  return data.items ?? [];
}

export async function createChatSession(payload: { title?: string; active_context?: AIWorkspaceContext }): Promise<AIChatSession> {
  const data = await requestJson<{ session: AIChatSession }>("/api/ai-workspace/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return data.session;
}

export async function getChatSession(sessionId: string): Promise<{ session: AIChatSession; history: AIChatMessage[] }> {
  return requestJson<{ session: AIChatSession; history: AIChatMessage[] }>(`/api/ai-workspace/sessions/${sessionId}`);
}

export async function renameChatSession(sessionId: string, title: string): Promise<AIChatSession> {
  const data = await requestJson<{ session: AIChatSession }>(`/api/ai-workspace/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return data.session;
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  await apiFetch(`/api/ai-workspace/sessions/${sessionId}`, { method: "DELETE" });
}

export async function sendChatMessage(payload: { session_id?: string | null; message: string; context?: AIWorkspaceContext | null }): Promise<AIChatResponse> {
  return requestJson<AIChatResponse>("/api/ai-workspace/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listMemories(): Promise<AIMemory[]> {
  const data = await requestJson<{ items: AIMemory[] }>("/api/ai-workspace/memory");
  return data.items ?? [];
}

export async function createMemory(payload: { memory_type: string; content: string; importance: number }): Promise<AIMemory> {
  const data = await requestJson<{ memory: AIMemory }>("/api/ai-workspace/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return data.memory;
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await apiFetch(`/api/ai-workspace/memory/${memoryId}`, { method: "DELETE" });
}

export async function analyzeLatestReport(reportId?: string): Promise<AIAnalysisResponse> {
  return requestJson<AIAnalysisResponse>("/api/ai-workspace/reports/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id: reportId ?? null }),
  });
}

export async function analyzeBugs(query = ""): Promise<AIAnalysisResponse> {
  return requestJson<AIAnalysisResponse>("/api/ai-workspace/bugs/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}

export async function analyzeScreenshots(reportId?: string, testRunId?: string): Promise<AIAnalysisResponse> {
  return requestJson<AIAnalysisResponse>("/api/ai-workspace/screenshots/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_id: reportId ?? null, test_run_id: testRunId ?? null }),
  });
}

export async function generateInstruction(topic: string): Promise<AIInstructionResponse> {
  return requestJson<AIInstructionResponse>("/api/ai-workspace/instructions/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
}

export async function getWorkspaceContext(query: string, reportId?: string, testRunId?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (reportId) params.set("report_id", reportId);
  if (testRunId) params.set("test_run_id", testRunId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return requestJson<Record<string, unknown>>(`/api/ai-workspace/context${suffix}`);
}

export async function getReportsOverview(reportId?: string, q?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (reportId) params.set("report_id", reportId);
  if (q) params.set("q", q);
  return requestJson<Record<string, unknown>>(`/api/ai-workspace/reports/overview${params.toString() ? `?${params.toString()}` : ""}`);
}

export async function getBugsOverview(): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>("/api/ai-workspace/bugs/overview");
}

export async function getScreenshotsOverview(reportId?: string, testRunId?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (reportId) params.set("report_id", reportId);
  if (testRunId) params.set("test_run_id", testRunId);
  return requestJson<Record<string, unknown>>(`/api/ai-workspace/screenshots/overview${params.toString() ? `?${params.toString()}` : ""}`);
}
