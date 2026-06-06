import { apiFetch, apiJson } from "@/services/http";

export interface ReportLibraryItem {
  report_id: string;
  report_type: "legacy" | "ai" | "multi_agent";
  report_label?: string;
  test_name: string;
  summary?: string | null;
  website: string;
  generated_date: string;
  status: string;
  score?: number | null;
  related_test_id?: string | null;
  related_bug_id?: string | null;
  test_type?: string | null;
  scenario_tree?: Record<string, unknown> | null;
  risk_summary?: Record<string, unknown> | null;
  objective_coverage?: Record<string, unknown>[] | null;
  bug_metadata?: BugReportMetadata | null;
}

export interface BugReportMetadata {
  severity: "low" | "medium" | "high" | "critical";
  fingerprint: string;
  lifecycle_status: string;
  occurrences: number;
  regression_count: number;
  first_seen_run_id?: string | null;
  last_seen_run_id?: string | null;
  step_name?: string | null;
  failure_category?: string | null;
  root_cause?: string | null;
}

export interface ReportLibraryResponse {
  items: ReportLibraryItem[];
}

export interface ReportExportRequest {
  format: "pdf" | "json" | "markdown" | "csv";
  includeScreenshots?: boolean;
  includeComparison?: boolean;
  comparisonRunId?: string | null;
  title?: string | null;
}

export interface ReportExportRecord {
  export_id: string;
  report_id: string;
  user_id?: string;
  format: string;
  file_path: string;
  title: string;
  include_screenshots?: boolean;
  include_comparison?: boolean;
  comparison_run_id?: string | null;
  file_size_bytes?: number;
  media_type?: string;
  download_url?: string;
  created_at?: string;
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

export async function getReports(query: ReportsQuery = {}): Promise<ReportLibraryResponse> {
  const qs = toQueryString(query);
  return apiJson<ReportLibraryResponse>(`/api/reports${qs}`);
}

export async function getReportById(reportId: string): Promise<ReportLibraryItem> {
  return apiJson<ReportLibraryItem>(`/api/reports/${encodeURIComponent(reportId)}`);
}

export async function downloadReport(reportId: string): Promise<Blob> {
  const response = await apiFetch(`/api/reports/${encodeURIComponent(reportId)}/download`);
  return response.blob();
}

export async function exportAllReports(query: ReportsQuery = {}): Promise<Blob> {
  const qs = toQueryString(query);
  const response = await apiFetch(`/api/reports/export-all${qs}`);
  return response.blob();
}

export async function createReportExport(reportId: string, payload: ReportExportRequest): Promise<ReportExportRecord> {
  return apiJson<ReportExportRecord>(`/api/intelligence/reports/${encodeURIComponent(reportId)}/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      format: payload.format,
      include_screenshots: payload.includeScreenshots ?? true,
      include_comparison: payload.includeComparison ?? false,
      comparison_run_id: payload.comparisonRunId ?? null,
      title: payload.title ?? null,
    }),
  });
}

export async function downloadReportExport(reportId: string, exportId: string): Promise<Blob> {
  const response = await apiFetch(`/api/intelligence/reports/${encodeURIComponent(reportId)}/exports/${encodeURIComponent(exportId)}/download`);
  if (!response.ok) {
    throw new Error(`Failed to download export: ${response.status}`);
  }
  return response.blob();
}
