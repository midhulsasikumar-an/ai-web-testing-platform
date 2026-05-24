import { apiFetch, apiJson, API_BASE_URL } from "@/services/http";

export interface ReportLibraryItem {
  report_id: string;
  report_type: "legacy" | "ai" | "multi_agent";
  report_label?: string;
  test_name: string;
  website: string;
  generated_date: string;
  status: string;
  score?: number | null;
  related_test_id?: string | null;
  related_bug_id?: string | null;
}

export interface ReportLibraryResponse {
  items: ReportLibraryItem[];
}

export interface ReportsQuery {
  q?: string;
  reportType?: string;
  status?: string;
}

function toQueryString(query: ReportsQuery): string {
  const params = new URLSearchParams();
  if (query.q?.trim()) {
    params.set("q", query.q.trim());
  }
  if (query.reportType?.trim()) {
    params.set("report_type", query.reportType.trim());
  }
  if (query.status?.trim()) {
    params.set("status", query.status.trim());
  }
  const value = params.toString();
  return value ? `?${value}` : "";
}

export async function getReports(query: ReportsQuery = {}, token?: string): Promise<ReportLibraryResponse> {
  const qs = toQueryString(query);
  const url = `${API_BASE_URL}/api/reports${qs}`;
  console.log("Reports URL:", url);
  return apiJson<ReportLibraryResponse>(`/api/reports${qs}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export async function downloadReport(reportId: string): Promise<Blob> {
  const url = `${API_BASE_URL}/api/reports/${reportId}/download`;
  console.log("Reports URL:", url);
  const response = await apiFetch(`/api/reports/${encodeURIComponent(reportId)}/download`);
  console.log("Status:", response.status);
  return response.blob();
}

export async function exportAllReports(query: ReportsQuery = {}): Promise<Blob> {
  const qs = toQueryString(query);
  const url = `${API_BASE_URL}/api/reports/export-all${qs}`;
  console.log("Reports URL:", url);
  const response = await apiFetch(`/api/reports/export-all${qs}`);
  console.log("Status:", response.status);
  return response.blob();
}
