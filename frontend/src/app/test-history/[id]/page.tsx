"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetadataField } from "@/components/shared/metadata-field";
import { formatDateLong, formatTime } from "@/lib/formatters";
import { DEFAULT_TEST_TYPE_CONFIG, resolveTestTypeConfig } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/services/http";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  ExternalLink,
  FileText,
  Globe,
  Image as ImageIcon,
  Lightbulb,
  Maximize2,
  Play,
  ShieldAlert,
  Sparkles,
  Terminal,
  X,
  XCircle,
} from "lucide-react";

type TestRecord = Record<string, any>;

type DetailResult = {
  test?: string;
  details?: unknown;
  status?: string;
  error?: string;
  step?: { action?: string; target?: string; value?: unknown };
};

type ScreenshotEvidence = {
  label: string;
  url: string;
};

type Finding = {
  tone: "success" | "warning" | "muted";
  text: string;
};

function normalizeArtifactUrl(value: string): string {
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/")) return `${API_BASE_URL}${value}`;
  return `${API_BASE_URL}/${value}`;
}

function stringifyValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function downloadTextFile(filename: string, content: string): void {
  if (typeof window === "undefined") return;
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function buildScreenshotEvidence(test: TestRecord): ScreenshotEvidence[] {
  const evidence: ScreenshotEvidence[] = [];
  const seen = new Set<string>();
  const add = (label: string, raw: unknown) => {
    let path = "";
    if (typeof raw === "string") {
      path = raw;
    } else if (raw && typeof raw === "object" && "path" in raw) {
      path = String((raw as { path?: unknown }).path ?? "");
    }
    const url = normalizeArtifactUrl(path);
    if (url && !seen.has(url)) {
      evidence.push({ label, url });
      seen.add(url);
    }
  };

  const screenshotPaths = Array.isArray(test.screenshot_paths) ? test.screenshot_paths : [];
  if (screenshotPaths.length > 0) {
    screenshotPaths.forEach((item: unknown, index: number) => add(`Screenshot ${index + 1}`, item));
    return evidence;
  }

  const aiReport = test.ai_report as Record<string, unknown> | undefined;
  if (Array.isArray(aiReport?.screenshots) && aiReport.screenshots.length > 0) {
    aiReport.screenshots.forEach((item: unknown, index: number) => add(`AI Report ${index + 1}`, item));
    return evidence;
  }

  const streamLogs = Array.isArray(test.stream_logs) ? test.stream_logs : [];
  for (let i = 0; i < streamLogs.length; i += 1) {
    const log = streamLogs[i] as Record<string, unknown>;
    const details = (log.details && typeof log.details === "object") ? (log.details as Record<string, unknown>) : undefined;
    const screenshot = details?.screenshot ?? log.screenshot;
    if (screenshot) add(`Stream ${i + 1}`, screenshot);
  }
  if (evidence.length > 0) return evidence;

  const screenshot = test.screenshot as Record<string, unknown> | undefined;
  if (screenshot?.home) add("Homepage", screenshot.home);
  if (Array.isArray(screenshot?.button_interactions)) {
    screenshot.button_interactions.forEach((item, index) => add(`Interaction ${index + 1}`, item));
  }

  const artifacts = test.artifacts as Record<string, unknown> | undefined;
  if (Array.isArray(artifacts?.screenshots)) {
    artifacts.screenshots.forEach((item: unknown, index: number) => add(`Artifact ${index + 1}`, item));
  }

  return evidence;
}

function buildFindings(test: TestRecord, results: DetailResult[], summaryText: string): Finding[] {
  const findings: Finding[] = [];
  const add = (tone: Finding["tone"], text: unknown) => {
    const value = stringifyValue(text).trim();
    if (value) findings.push({ tone, text: value });
  };

  const insights = test.insights as Record<string, unknown> | undefined;
  if (insights) {
    (Array.isArray(insights.critical) ? insights.critical : []).forEach((item) => add("warning", item));
    (Array.isArray(insights.moderate) ? insights.moderate : []).forEach((item) => add("warning", item));
    (Array.isArray(insights.minor) ? insights.minor : []).forEach((item) => add("success", item));
  }

  const priorityIssues = Array.isArray(test.priority_issues) ? test.priority_issues : [];
  priorityIssues.forEach((item: { level?: string; issue?: string }) => {
    add(item.level === "critical" || item.level === "moderate" ? "warning" : "muted", `${item.level ?? "info"}: ${item.issue ?? "Issue detected"}`);
  });

  if (!findings.length) {
    const passed = results.filter((step) => step.status === "pass").length;
    const failed = results.filter((step) => step.status === "fail").length;
    add("success", `${passed} step(s) passed`);
    if (failed > 0) add("warning", `${failed} step(s) failed`);
    add("muted", test.ai_summary || summaryText || "No AI summary available.");
  }

  return findings.slice(0, 6);
}

function buildRecommendations(test: TestRecord, results: DetailResult[], screenshotCount: number): string[] {
  if (Array.isArray(test.recommendations) && test.recommendations.length > 0) {
    return test.recommendations.map((item: unknown) => stringifyValue(item)).filter(Boolean);
  }

  const fallback: string[] = [];
  if (results.some((step) => step.status === "fail")) fallback.push("Review failed steps and selector stability.");
  if (!screenshotCount) fallback.push("Capture screenshots on critical actions for easier debugging.");
  if (!fallback.length) fallback.push("No additional recommendations available.");
  return fallback;
}

export default function TestDetailPage() {
  const params = useParams();
  const { getTestById } = useBugContext();
  const test = getTestById(params.id as string) as TestRecord | null;
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);

  const testRecord = test ?? {};

  const summaryText = useMemo(() => {
    if (!test) return "";
    if (typeof test.summary === "string") return test.summary;
    if (test.summary) return stringifyValue(test.summary);
    return "No summary available";
  }, [test]);

  const reportText = useMemo(() => {
    if (!test) return "";
    if (typeof test.report === "string") return test.report;
    if (test.report) return stringifyValue(test.report);
    return "";
  }, [test]);

  const results = useMemo<DetailResult[]>(() => {
    return Array.isArray(test?.results) ? (test?.results as DetailResult[]) : [];
  }, [test]);

  const screenshotEvidence = useMemo(() => buildScreenshotEvidence(testRecord), [testRecord]);
  const findings = useMemo(() => buildFindings(testRecord, results, summaryText), [results, summaryText, testRecord]);
  const recommendations = useMemo(() => buildRecommendations(testRecord, results, screenshotEvidence.length), [results, screenshotEvidence.length, testRecord]);

  const typeConfig = resolveTestTypeConfig(test?.test_type);
  const TypeIcon = typeConfig.icon ?? DEFAULT_TEST_TYPE_CONFIG.icon;
  const typeLabel = typeConfig.label ?? DEFAULT_TEST_TYPE_CONFIG.label;
  const statusLabel = test?.overall_status ?? test?.status ?? "unknown";
  const aiPlan = test?.ai_plan ?? null;
  const streamLogs = Array.isArray(test?.stream_logs) ? test.stream_logs : [];
  const artifacts = test?.artifacts && typeof test.artifacts === "object" ? (test.artifacts as Record<string, unknown>) : null;
  const previewShot = previewIndex !== null ? screenshotEvidence[previewIndex] ?? null : null;

  const downloadReport = () => downloadTextFile(`test-${test?.test_id ?? "run"}-report.txt`, reportText || summaryText || "No report available");
  const downloadLogs = () => downloadTextFile(`test-${test?.test_id ?? "run"}-logs.json`, JSON.stringify(streamLogs, null, 2));
  const downloadScreenshots = () => downloadTextFile(`test-${test?.test_id ?? "run"}-screenshots.json`, JSON.stringify(screenshotEvidence, null, 2));

  if (!test) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Terminal className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-muted-foreground font-medium">Test not found.</p>
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Link>
      </div>
    );
  }

  const mainStatus = statusLabel === "pass" ? "pass" : statusLabel === "warning" ? "warning" : statusLabel === "fail" ? "fail" : "unknown";

  return (
    <>
      <Header title="Test Log Details">
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Link>
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          Re-run
        </Link>
      </Header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] items-start">
        <div className="min-w-0 space-y-6">
          <Card className={
            mainStatus === "pass"
              ? "border-green-500/30 bg-gradient-to-r from-green-50/50 to-transparent"
              : mainStatus === "warning"
              ? "border-yellow-500/30 bg-gradient-to-r from-yellow-50/50 to-transparent"
              : "border-red-500/30 bg-gradient-to-r from-red-50/50 to-transparent"
          }>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl shrink-0 ${mainStatus === "pass" ? "bg-green-100" : "bg-red-100"}`}>
                  {mainStatus === "pass" ? (
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                  ) : mainStatus === "warning" ? (
                    <AlertTriangle className="h-6 w-6 text-yellow-500" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold">
                      {mainStatus === "pass" ? "Test Passed" : mainStatus === "warning" ? "Test Warning" : "Test Failed"}
                    </h2>
                    <Badge variant={mainStatus === "pass" ? "secondary" : "destructive"}>{statusLabel}</Badge>
                  </div>

                  <div className="mt-3 rounded-lg border border-border bg-background/60 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <p className="text-sm font-semibold">AI Executive Summary</p>
                    </div>

                    <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                      {stringifyValue(test.ai_summary || summaryText || "No AI summary available")}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Test Results</CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
              {results.length > 0 ? (
                results.map((result, index) => (
                  <div key={index} className="flex items-start justify-between gap-4 border rounded-lg p-3">
                    <div className="min-w-0">
                      <p className="font-medium break-words">
                        {stringifyValue(result.test || result.step?.action || result.error || `Step ${index + 1}`)}
                      </p>
                      {Boolean(result.details) && (
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap break-words">
                          {typeof result.details === "string" ? result.details : stringifyValue(result.details)}
                        </p>
                      )}
                      {!Boolean(result.details) && Boolean(result.error) && (
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap break-words">{result.error}</p>
                      )}
                    </div>

                    <Badge variant={result.status === "pass" ? "secondary" : result.status === "fail" ? "destructive" : "outline"}>
                      {result.status || "info"}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-sm text-muted-foreground">
                  No test results available.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
              <CardTitle className="flex items-center gap-2">
                <ImageIcon className="h-5 w-5 text-primary" />
                Screenshot Evidence
              </CardTitle>
              {screenshotEvidence.length > 0 && (
                <button className="text-sm font-medium text-primary hover:underline" onClick={() => setPreviewIndex(0)}>
                  View All ({screenshotEvidence.length})
                </button>
              )}
            </CardHeader>

            <CardContent>
              {screenshotEvidence.length > 0 ? (
                <div className="flex gap-3 overflow-x-auto pb-2 snap-x">
                  {screenshotEvidence.map((shot, index) => (
                    <button
                      key={`${shot.url}-${index}`}
                      className="group w-56 shrink-0 snap-start overflow-hidden rounded-xl border border-border bg-muted/20 text-left"
                      onClick={() => setPreviewIndex(index)}
                    >
                      <div className="aspect-[4/3] bg-slate-100 overflow-hidden">
                        <img src={shot.url} alt={shot.label} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
                      </div>
                      <div className="flex items-center justify-between gap-2 p-2">
                        <span className="text-xs font-medium truncate">{shot.label}</span>
                        <Maximize2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-muted/10 p-6 text-sm text-muted-foreground">
                  No screenshots captured during this run.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-emerald-500" />
                AI Findings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {findings.map((item, index) => (
                <div key={index} className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 p-3">
                  {item.tone === "success" ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-500" />
                  ) : item.tone === "warning" ? (
                    <AlertCircle className="mt-0.5 h-4 w-4 text-amber-500" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-4 w-4 text-slate-400" />
                  )}
                  <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap break-words">{item.text}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 p-3">
                  <ChevronRight className="mt-0.5 h-4 w-4 text-blue-500" />
                  <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{recommendation}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" />
                Artifacts
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadReport}>
                <FileText className="mr-2 h-4 w-4" />
                Download Report
              </button>
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadLogs}>
                <Terminal className="mr-2 h-4 w-4" />
                Download Logs
              </button>
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadScreenshots}>
                <ImageIcon className="mr-2 h-4 w-4" />
                Download Screenshots
              </button>
            </CardContent>
          </Card>

          {Array.isArray(test.priority_issues) && test.priority_issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-red-500" />
                  Priority Issues
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {test.priority_issues.map((issue: { level?: string; issue?: string }, index: number) => (
                  <div key={index} className="rounded-lg border border-border p-4 bg-muted/20">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium break-words">{issue.issue || "Priority issue detected"}</p>
                      <Badge variant={issue.level === "critical" ? "destructive" : issue.level === "moderate" ? "outline" : "secondary"}>
                        {issue.level || "info"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-4 self-start sticky top-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Test Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MetadataField icon={Terminal} label="Test ID">
                <p className="text-sm font-mono font-medium break-all">{test.test_id}</p>
              </MetadataField>

              <MetadataField icon={Globe} label="Target URL">
                <a href={test.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline flex items-center gap-1 break-all">
                  {test.url}
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              </MetadataField>

              <MetadataField icon={TypeIcon} label="Test Type">
                <div className="flex items-center gap-1.5">
                  <TypeIcon className="h-3.5 w-3.5 text-primary" />
                  <span className="text-sm font-medium">{typeLabel}</span>
                </div>
              </MetadataField>

              <MetadataField icon={Clock} label="Health Score">
                <p className="text-sm font-mono font-medium">{test.health_score ?? 0}/100</p>
              </MetadataField>

              <MetadataField icon={Calendar} label="Timestamp">
                <div className="text-sm">
                  <p>{formatDateLong(test.created_at || "")}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(test.created_at || "")}</p>
                </div>
              </MetadataField>

              <MetadataField icon={Clock} label="Duration">
                <p className="text-sm font-mono font-medium">{typeof test.duration !== "undefined" ? String(test.duration) : "—"}</p>
              </MetadataField>

              <MetadataField icon={mainStatus === "pass" ? CheckCircle2 : XCircle} label="Result">
                <Badge variant={mainStatus === "pass" ? "secondary" : "destructive"}>{statusLabel}</Badge>
              </MetadataField>
            </CardContent>
          </Card>

          {aiPlan && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  AI Plan
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm font-medium leading-relaxed">{stringifyValue(aiPlan.summary)}</p>
                <p className="text-xs text-muted-foreground whitespace-pre-wrap">{stringifyValue(aiPlan.instruction)}</p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" />
                Execution Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              {streamLogs.length > 0 ? (
                <div className="max-h-[360px] overflow-y-auto pr-1 space-y-2">
                  {streamLogs.map((log: { time?: string; level?: string; msg?: string; message?: string }, index: number) => (
                    <div key={index} className="rounded-lg border border-border bg-muted/20 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-mono text-muted-foreground">{log.time || ""}</p>
                        <Badge variant={log.level === "error" ? "destructive" : log.level === "warn" ? "outline" : "secondary"}>
                          {log.level || "info"}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm whitespace-pre-line break-words">{log.msg || log.message || "Log entry"}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-muted/10 p-6 text-sm text-muted-foreground">
                  No execution logs captured.
                </div>
              )}
            </CardContent>
          </Card>

          {artifacts && Object.keys(artifacts).length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Artifacts Preview</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs whitespace-pre-wrap break-words rounded-lg border border-border bg-muted/20 p-3 max-h-64 overflow-auto">
                  {JSON.stringify(artifacts, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {previewShot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setPreviewIndex(null)}>
          <div className="relative w-full max-w-6xl overflow-hidden rounded-2xl bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <p className="text-sm font-semibold">Screenshot Preview</p>
                <p className="text-xs text-muted-foreground">{previewShot.label}</p>
              </div>
              <button className={cn(buttonVariants({ variant: "ghost", size: "sm" }))} onClick={() => setPreviewIndex(null)}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_220px]">
              <div className="flex min-h-[52vh] items-center justify-center overflow-hidden rounded-2xl bg-slate-100 p-3">
                <img src={previewShot.url} alt={previewShot.label} className="max-h-[78vh] w-auto rounded-xl border border-border object-contain" />
              </div>

              <div className="max-h-[78vh] overflow-y-auto space-y-2 pr-1">
                {screenshotEvidence.map((shot, index) => (
                  <button
                    key={`${shot.url}-${index}`}
                    className={`w-full overflow-hidden rounded-xl border text-left transition ${index === previewIndex ? "border-primary ring-2 ring-primary/20" : "border-border"}`}
                    onClick={() => setPreviewIndex(index)}
                  >
                    <div className="aspect-[4/3] bg-slate-100 overflow-hidden">
                      <img src={shot.url} alt={shot.label} className="h-full w-full object-cover" />
                    </div>
                    <div className="px-3 py-2 text-xs font-medium truncate">{shot.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
