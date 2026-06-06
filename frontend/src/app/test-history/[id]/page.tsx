"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  ExternalLink,
  FileText,
  Globe,
  Play,
  Sparkles,
  Terminal,
  XCircle,
} from "lucide-react";

import { Header } from "@/components/layout/header";
import { DashboardSection } from "@/components/shared/dashboard-section";
import { ScreenshotGallery } from "@/components/shared/screenshot-gallery";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetadataField } from "@/components/shared/metadata-field";
import { useBugContext } from "@/context/bug-context";
import { formatDateLong, formatTime } from "@/lib/formatters";
import { DEFAULT_TEST_TYPE_CONFIG, resolveTestTypeConfig } from "@/lib/constants";
import { resolveTestDisplayName } from "@/lib/test-display";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/services/http";
import { getTestById as fetchTestById } from "@/services/test-api";

const RERUN_CONFIG_KEY = "test_history_rerun_config";

// The backend returns a flexible test-run document with dynamic report fields.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type TestRecord = Record<string, any>;

type DetailResult = {
  test?: string;
  details?: unknown;
  status?: string;
  error?: string;
  step?: { action?: string; target?: string; value?: unknown };
  failure_category?: string | null;
  root_cause?: string | null;
  root_cause_confidence?: number | null;
  scenario_id?: string | null;
  scenario_name?: string | null;
  passed_steps?: number;
  failed_steps?: number;
  executed_steps?: number;
  step_results?: TestStepView[];
};

type TestStepView = {
  step_index?: number;
  step_name?: string;
  status?: "passed" | "failed" | "warning";
  error?: string | null;
  details?: string | null;
  duration_ms?: number | null;
};

type ScreenshotEvidence = {
  label: string;
  url: string;
};

type Finding = {
  tone: "success" | "warning" | "muted";
  text: string;
};

type ResultViewMode = "human" | "json";
type SectionKey =
  | "summary"
  | "results"
  | "coverage"
  | "scenarioTree"
  | "riskSummary"
  | "screenshots"
  | "findings"
  | "lifecycle"
  | "bugs"
  | "recommendations"
  | "priorityIssues"
  | "logs"
  | "artifacts";

function normalizeArtifactUrl(value: string): string {
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/")) return `${API_BASE_URL}${value}`;
  return `${API_BASE_URL}/${value}`;
}

function readArtifactUrl(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const candidate = record.artifact_url ?? record.path ?? record.url;
    if (typeof candidate === "string") return candidate;
  }
  return "";
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

function buildHumanReadableResult(result: DetailResult): string[] {
  const lines: string[] = [];
  const details = result.details && typeof result.details === "object" ? (result.details as Record<string, unknown>) : null;
  const source = details ?? (result as Record<string, unknown>);

  const urlChanged = source.url_changed;
  if (typeof urlChanged === "boolean") {
    lines.push(urlChanged ? "✓ URL changed successfully" : "✗ URL did not change");
  }

  const errorDetected = source.error_detected;
  if (typeof errorDetected === "boolean") {
    lines.push(errorDetected ? "✗ Error detected" : "✓ No errors detected");
  }

  const expectedMatched = source.expected_matched;
  if (typeof expectedMatched === "boolean") {
    lines.push(expectedMatched ? "✓ Expected result matched" : "✗ Expected result did not match");
  }

  const title = source.title;
  if (typeof title === "string" && title.trim()) {
    lines.push(`✓ Page title verified: ${title.trim()}`);
  }

  const url = source.url;
  if (typeof url === "string" && url.trim()) {
    lines.push(`✓ Final URL: ${url.trim()}`);
  }

  if (!lines.length && result.error) {
    lines.push(`✗ ${result.error}`);
  }

  if (!lines.length) {
    if (result.status === "pass") {
      lines.push("✓ Step passed successfully");
    } else if (result.status === "fail") {
      lines.push("✗ Step failed");
    } else {
      lines.push("• No structured summary available");
    }
  }

  return lines;
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
    const path = readArtifactUrl(raw);
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
    const details = log.details && typeof log.details === "object" ? (log.details as Record<string, unknown>) : undefined;
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

function formatLifecycleStatus(value: string): string {
  return value.toLowerCase().split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function formatRootCause(value: string): string {
  return value.toLowerCase().split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

export default function TestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { getTestById } = useBugContext();
  const test = getTestById(params.id as string) as TestRecord | null;
  const [remoteTest, setRemoteTest] = useState<TestRecord | null>(null);
  const [loadingRemote, setLoadingRemote] = useState(true);
  const [resultViewModes, setResultViewModes] = useState<Record<number, ResultViewMode>>({});
  const [compactMode, setCompactMode] = useState(true);
  const [visibleResultCount, setVisibleResultCount] = useState(24);
  const [visibleLogCount, setVisibleLogCount] = useState(24);
  const [sectionOpen, setSectionOpen] = useState<Record<SectionKey, boolean>>({
    summary: true,
    results: false,
    coverage: false,
    scenarioTree: false,
    riskSummary: false,
    screenshots: false,
    findings: false,
    lifecycle: false,
    bugs: false,
    recommendations: false,
    priorityIssues: false,
    logs: false,
    artifacts: false,
  });

  const activeTest = test ?? remoteTest;
  const testRecord = useMemo<TestRecord>(() => activeTest ?? {}, [activeTest]);

  const summaryText = useMemo(() => {
    if (!activeTest) return "";
    if (typeof activeTest.summary === "string") return activeTest.summary;
    if (activeTest.summary) return stringifyValue(activeTest.summary);
    return "No summary available";
  }, [activeTest]);

  const reportText = useMemo(() => {
    if (!activeTest) return "";
    if (typeof activeTest.report === "string") return activeTest.report;
    if (activeTest.report) return stringifyValue(activeTest.report);
    return "";
  }, [activeTest]);

  const results = useMemo<DetailResult[]>(() => Array.isArray(activeTest?.results) ? (activeTest?.results as DetailResult[]) : [], [activeTest]);
  const riskSummary = useMemo<Record<string, unknown> | null>(() => {
    const fromTest = activeTest?.risk_summary && typeof activeTest.risk_summary === "object" ? (activeTest.risk_summary as Record<string, unknown>) : null;
    const aiReport = activeTest?.ai_report && typeof activeTest.ai_report === "object" ? (activeTest.ai_report as Record<string, unknown>) : null;
    const fromReport = aiReport?.risk_summary && typeof aiReport.risk_summary === "object" ? (aiReport.risk_summary as Record<string, unknown>) : null;
    return fromTest ?? fromReport ?? null;
  }, [activeTest]);
  const screenshotEvidence = useMemo(() => buildScreenshotEvidence(testRecord), [testRecord]);
  const findings = useMemo(() => buildFindings(testRecord, results, summaryText), [results, summaryText, testRecord]);
  const recommendations = useMemo(() => buildRecommendations(testRecord, results, screenshotEvidence.length), [results, screenshotEvidence.length, testRecord]);
  const visibleResults = useMemo(() => results.slice(0, visibleResultCount), [results, visibleResultCount]);
  const streamLogs = useMemo(
    () => (Array.isArray(activeTest?.stream_logs) ? activeTest.stream_logs : []),
    [activeTest],
  );
  const visibleLogs = useMemo(() => streamLogs.slice(0, visibleLogCount) as Array<{ time?: string; level?: string; msg?: string; message?: string }>, [streamLogs, visibleLogCount]);
  const artifacts = activeTest?.artifacts && typeof activeTest.artifacts === "object" ? (activeTest.artifacts as Record<string, unknown>) : null;
  const aiPlan = activeTest?.ai_plan ?? null;

  const typeConfig = resolveTestTypeConfig(activeTest?.test_type);
  const TypeIcon = typeConfig.icon ?? DEFAULT_TEST_TYPE_CONFIG.icon;
  const typeLabel = typeConfig.label ?? DEFAULT_TEST_TYPE_CONFIG.label;
  const statusLabel = activeTest?.overall_status ?? activeTest?.status ?? "unknown";
  const mainStatus = statusLabel === "pass" ? "pass" : statusLabel === "warning" ? "warning" : statusLabel === "fail" ? "fail" : "unknown";

  const downloadReport = () => downloadTextFile(`test-${activeTest?.test_id ?? "run"}-report.txt`, reportText || summaryText || "No report available");
  const downloadLogs = () => downloadTextFile(`test-${activeTest?.test_id ?? "run"}-logs.json`, JSON.stringify(streamLogs, null, 2));
  const downloadScreenshots = () => downloadTextFile(`test-${activeTest?.test_id ?? "run"}-screenshots.json`, JSON.stringify(screenshotEvidence, null, 2));

  useEffect(() => {
    const id = String(params.id || "");
    if (!id || test) return;

    let active = true;

    fetchTestById(id)
      .then((t) => {
        if (!active) return;
        setRemoteTest(t as TestRecord);
      })
      .catch((err) => {
        console.error("Failed to fetch test by id:", err);
      })
      .finally(() => {
        if (active) setLoadingRemote(false);
      });

    return () => {
      active = false;
    };
  }, [params.id, test]);

  const handleRerun = () => {
    const historicalPlan = activeTest?.ai_plan && typeof activeTest.ai_plan === "object" ? (activeTest.ai_plan as Record<string, unknown>) : null;
    const resolvedName = resolveTestDisplayName(activeTest);
    const rerunConfig = {
      targetUrl: String(activeTest?.target_url || activeTest?.url || ""),
      testName: resolvedName === "Untitled Test" ? "" : resolvedName,
      goal: String(activeTest?.goal || historicalPlan?.instruction || activeTest?.ai_summary || summaryText || ""),
      testType: String(activeTest?.test_type || activeTest?.run_type || "e2e"),
      browser: String(activeTest?.browser || activeTest?.execution_settings?.browser || ""),
      device: String(activeTest?.device || activeTest?.execution_settings?.device || ""),
      coverageLevel: String(activeTest?.coverage_level || activeTest?.execution_settings?.coverage_level || historicalPlan?.coverage_level || ""),
      executionSettings: activeTest?.execution_settings || historicalPlan?.execution_settings || null,
      aiPlan: activeTest?.ai_plan ?? null,
    };

    window.localStorage.setItem(RERUN_CONFIG_KEY, JSON.stringify(rerunConfig));
    router.push("/run-test");
  };

  if (!activeTest && loadingRemote) {
    return <div className="flex h-[60vh] items-center justify-center p-8 text-sm text-slate-500">Loading test...</div>;
  }

  if (!activeTest) {
    return <div className="flex h-[60vh] items-center justify-center p-8 text-sm text-slate-500">Test not found.</div>;
  }

  return (
    <>
      <Header title="Test Log Details" eyebrow="Results">
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
        <button type="button" onClick={handleRerun} className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="mr-2 h-4 w-4" />
          Re-run
        </button>
      </Header>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-white p-3 shadow-xs-token">
        <Badge variant={mainStatus === "pass" ? "secondary" : mainStatus === "warning" ? "outline" : "destructive"}>{statusLabel}</Badge>
        <Badge variant="outline">Duration {typeof activeTest?.duration !== "undefined" ? String(activeTest?.duration) : "—"}</Badge>
        <Badge variant="outline">Passed {results.filter((step) => step.status === "pass").length}</Badge>
        <Badge variant="outline">Failed {results.filter((step) => step.status === "fail").length}</Badge>
        <Badge variant="outline">Bugs {Array.isArray(activeTest?.priority_issues) ? activeTest.priority_issues.length : 0}</Badge>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => setCompactMode((current) => !current)} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            {compactMode ? "Dense View" : "Compact View"}
          </button>
          <button type="button" onClick={downloadReport} className={cn(buttonVariants({ size: "sm" }))}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      <div className={cn("grid items-start gap-6", compactMode ? "xl:grid-cols-[minmax(0,1fr)_320px]" : "xl:grid-cols-[minmax(0,1fr)_360px]") }>
        <div className="min-w-0 space-y-6">
          <Card className="border-border shadow-sm">
            <CardContent className="space-y-4 pt-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={mainStatus === "pass" ? "secondary" : mainStatus === "warning" ? "outline" : "destructive"}>{statusLabel}</Badge>
                    <Badge variant="outline">{typeLabel}</Badge>
                    <Badge variant="outline">{activeTest?.test_type ?? "full"}</Badge>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">{resolveTestDisplayName(activeTest)}</h1>
                    <p className="mt-1 max-w-3xl break-words text-sm text-slate-500">{activeTest?.website || activeTest?.url || "No website recorded"}</p>
                  </div>
                  <p className="max-w-3xl text-sm leading-relaxed text-slate-600">{stringifyValue(activeTest?.ai_summary || summaryText || "No AI summary available").slice(0, 600)}</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  ["Generated", activeTest?.created_at || "—"],
                  ["Related Test", activeTest?.related_test_id || "-"],
                  ["Related Bug", activeTest?.related_bug_id || "-"],
                  ["Health Score", `${activeTest?.health_score ?? 0}/100`],
                ].map(([label, value]) => (
                  <div key={label as string} className="rounded-lg border border-border bg-white p-4">
                    <p className="text-eyebrow">{label}</p>
                    <p className="mt-2 break-words text-sm font-semibold text-slate-900">{String(value)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <DashboardSection
            id="results"
            title="Test Results"
            description="Step-by-step execution output with human and JSON views."
            compact={compactMode}
            defaultOpen={sectionOpen.results}
            open={sectionOpen.results}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, results: open }))}
            storageKey="test-history-detail:results"
            className="shadow-sm"
            contentClassName={cn("space-y-3", compactMode ? "max-h-[42rem] overflow-y-auto pr-1" : "max-h-[34rem] overflow-y-auto pr-1")}
          >
            {results.length > 0 ? (
              <>
                {visibleResults.map((result, index) => (
                  <div key={index} className="overflow-hidden rounded-lg border border-border bg-white">
                    <div className="flex flex-col gap-3 border-b border-border bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900 break-words">{stringifyValue(result.test || result.step?.action || result.error || `Step ${index + 1}`)}</p>
                        <p className="text-xs text-slate-500">Result {index + 1}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant={result.status === "pass" ? "secondary" : result.status === "fail" ? "destructive" : "outline"}>{result.status || "info"}</Badge>
                        <div className="inline-flex rounded-full border border-border bg-white p-1 text-xs">
                          {["human", "json"].map((mode) => (
                            <button
                              key={mode}
                              type="button"
                              onClick={() => setResultViewModes((current) => ({ ...current, [index]: mode as ResultViewMode }))}
                              className={cn(
                                "rounded-full px-3 py-1.5 font-medium transition-colors",
                                (resultViewModes[index] ?? "human") === mode ? "bg-primary text-primary-foreground" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                              )}
                            >
                              {mode === "human" ? "Human Readable" : "JSON"}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="px-4 py-4">
                      {(resultViewModes[index] ?? "human") === "json" ? (
                        <pre className="max-h-72 overflow-auto rounded-lg border border-border bg-slate-950 px-4 py-3 text-xs leading-relaxed text-slate-100 whitespace-pre-wrap break-words">{JSON.stringify(result, null, 2)}</pre>
                      ) : (
                        <div className="space-y-2">
                          {buildHumanReadableResult(result).map((line, lineIndex) => (
                            <div key={lineIndex} className="flex items-start gap-3 rounded-lg border border-border bg-slate-50 px-3 py-2">
                              <span className="mt-0.5 text-sm">{line.startsWith("✗") ? "✗" : "✓"}</span>
                              <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap break-words">{line.replace(/^[✓✗•]\s*/, "")}</p>
                            </div>
                          ))}
                          {result.status === "fail" ? (
                            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 space-y-2">
                              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                                <div>
                                  <p className="text-eyebrow text-amber-700">Failure Category</p>
                                  <p className="mt-1 text-sm font-medium text-slate-800">{formatLifecycleStatus(String((result as DetailResult).failure_category || "UNKNOWN"))}</p>
                                </div>
                                <div>
                                  <p className="text-eyebrow text-amber-700">Root Cause</p>
                                  <p className="mt-1 text-sm font-medium text-slate-800">{formatRootCause(String((result as DetailResult).root_cause || "UNKNOWN"))}</p>
                                </div>
                                <div>
                                  <p className="text-eyebrow text-amber-700">Confidence</p>
                                  <p className="mt-1 text-sm font-medium text-slate-800">{Math.round(((result as DetailResult).root_cause_confidence || 0) * 100)}%</p>
                                </div>
                              </div>
                            </div>
                          ) : null}
                          {Array.isArray((result as DetailResult).step_results) && (result as DetailResult).step_results && (result as DetailResult).step_results!.length > 0 ? (
                            <div className="rounded-lg border border-border bg-slate-50 px-3 py-3 space-y-2">
                              <div className="flex items-center justify-between">
                                <p className="text-eyebrow text-slate-700">Step Breakdown</p>
                                <p className="text-xs text-slate-500">
                                  {(result as DetailResult).passed_steps ?? 0} passed · {(result as DetailResult).failed_steps ?? 0} failed
                                </p>
                              </div>
                              <ul className="space-y-1.5">
                                {((result as DetailResult).step_results ?? []).map((step) => {
                                  const status = (step.status || "warning") as "passed" | "failed" | "warning";
                                  const badgeVariant = status === "passed" ? "secondary" : status === "failed" ? "destructive" : "outline";
                                  const icon = status === "passed" ? "✓" : status === "failed" ? "✗" : "•";
                                  return (
                                    <li key={step.step_index ?? step.step_name} className="flex items-start gap-3 rounded-md border border-border bg-white px-3 py-2">
                                      <span className="mt-0.5 text-sm text-slate-500 w-6 text-right">{step.step_index ?? "·"}</span>
                                      <span className="mt-0.5 text-sm">{icon}</span>
                                      <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-slate-800 break-words">{step.step_name || `Step ${step.step_index ?? ""}`}</p>
                                        {step.status === "failed" && (step.error || step.details) ? (
                                          <p className="text-xs text-rose-600 mt-0.5 break-words">
                                            {step.error || step.details}
                                          </p>
                                        ) : null}
                                      </div>
                                      <Badge variant={badgeVariant as "secondary" | "destructive" | "outline"} className="shrink-0">
                                        {status}
                                      </Badge>
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {visibleResultCount < results.length ? (
                  <div className="flex justify-center pt-1">
                    <button type="button" className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={() => setVisibleResultCount((current) => current + 24)}>
                      Show more steps ({results.length - visibleResultCount})
                    </button>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-sm text-muted-foreground">No test results available.</div>
            )}
          </DashboardSection>



          <DashboardSection
            id="riskSummary"
            title="Risk Summary"
            description="Aggregated risk signals captured for this run."
            compact={compactMode}
            defaultOpen={sectionOpen.riskSummary}
            open={sectionOpen.riskSummary}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, riskSummary: open }))}
            storageKey="test-history-detail:risk-summary"
            className="shadow-sm"
            contentClassName={cn("space-y-2", compactMode ? "max-h-[20rem] overflow-y-auto pr-1" : "max-h-[18rem] overflow-y-auto pr-1")}
          >
            {riskSummary ? (
              Object.entries(riskSummary)
                .filter(([, value]) => Boolean(value))
                .map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-lg border border-border bg-slate-50 px-3 py-2 text-sm">
                    <span className="text-slate-600 capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="font-semibold text-slate-900">{String(value)}</span>
                  </div>
                ))
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-sm text-muted-foreground">No risk summary available for this run.</div>
            )}
          </DashboardSection>

          <DashboardSection
            id="screenshots"
            title="Screenshot Collections"
            description="Grid-based evidence gallery with lazy loading and a lightbox preview."
            compact={compactMode}
            defaultOpen={sectionOpen.screenshots}
            open={sectionOpen.screenshots}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, screenshots: open }))}
            storageKey="test-history-detail:screenshots"
            className="shadow-sm"
            contentClassName={cn(compactMode ? "max-h-[28rem] overflow-y-auto pr-1" : "max-h-[24rem] overflow-y-auto pr-1")}
          >
            <ScreenshotGallery
              items={screenshotEvidence}
              title="Screenshot Evidence"
              description="Grid-based evidence gallery with lazy loading and a lightbox preview."
              compact={compactMode}
              initialVisibleCount={compactMode ? 8 : 12}
              loadMoreStep={compactMode ? 8 : 12}
              className="shadow-sm"
              maxBodyClassName="max-h-none overflow-visible p-0"
              emptyText="No screenshots captured during this run."
              showHeader={false}
            />
          </DashboardSection>

          <DashboardSection
            id="findings"
            title="AI Findings"
            description="Concise AI-generated observations from this run."
            compact={compactMode}
            defaultOpen={sectionOpen.findings}
            open={sectionOpen.findings}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, findings: open }))}
            storageKey="test-history-detail:findings"
            className="shadow-sm"
            contentClassName={cn("space-y-2", compactMode ? "max-h-[18rem] overflow-y-auto pr-1" : "max-h-[16rem] overflow-y-auto pr-1")}
          >
            {findings.map((item, index) => (
              <div key={index} className="flex items-start gap-3 rounded-lg border border-border bg-slate-50/60 p-3">
                {item.tone === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-500" /> : item.tone === "warning" ? <AlertCircle className="mt-0.5 h-4 w-4 text-amber-500" /> : <AlertTriangle className="mt-0.5 h-4 w-4 text-slate-400" />}
                <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap break-words">{item.text}</p>
              </div>
            ))}
          </DashboardSection>



          <DashboardSection
            id="recommendations"
            title="Recommendations"
            description="Lower-priority follow-up actions and remediation hints."
            compact={compactMode}
            defaultOpen={sectionOpen.recommendations}
            open={sectionOpen.recommendations}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, recommendations: open }))}
            storageKey="test-history-detail:recommendations"
            className="shadow-sm"
            contentClassName={cn("space-y-2", compactMode ? "max-h-[16rem] overflow-y-auto pr-1" : "max-h-[14rem] overflow-y-auto pr-1")}
          >
            {recommendations.map((recommendation, index) => (
              <div key={index} className="flex items-start gap-3 rounded-lg border border-border bg-slate-50/60 p-3">
                <ChevronRight className="mt-0.5 h-4 w-4 text-primary" />
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{recommendation}</p>
              </div>
            ))}
          </DashboardSection>

          <DashboardSection
            id="priorityIssues"
            title="Priority Issues"
            description="High-signal issues worth addressing first."
            compact={compactMode}
            defaultOpen={sectionOpen.priorityIssues}
            open={sectionOpen.priorityIssues}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, priorityIssues: open }))}
            storageKey="test-history-detail:priority-issues"
            className="shadow-sm"
            contentClassName={cn("space-y-3", compactMode ? "max-h-[14rem] overflow-y-auto pr-1" : "max-h-[12rem] overflow-y-auto pr-1")}
          >
            {Array.isArray(activeTest?.priority_issues) && activeTest.priority_issues.length > 0 ? activeTest.priority_issues.map((issue: { level?: string; issue?: string }, index: number) => (
              <div key={index} className="rounded-lg border border-border p-4 bg-slate-50/60">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium break-words">{issue.issue || "Priority issue detected"}</p>
                  <Badge variant={issue.level === "critical" ? "destructive" : issue.level === "moderate" ? "outline" : "secondary"}>{issue.level || "info"}</Badge>
                </div>
              </div>
            )) : <div className="rounded-lg border border-dashed border-border bg-slate-50 p-6 text-sm text-muted-foreground">No priority issues captured for this run.</div>}
          </DashboardSection>
        </div>

        <div className="space-y-4 self-start sticky top-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Test Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MetadataField icon={Terminal} label="Test ID"><p className="text-sm font-mono font-medium break-all">{activeTest?.test_id}</p></MetadataField>
              <MetadataField icon={Globe} label="Target URL"><a href={activeTest?.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 break-all text-xs text-primary hover:underline">{activeTest?.url}<ExternalLink className="h-3 w-3 shrink-0" /></a></MetadataField>
              <MetadataField icon={TypeIcon} label="Test Type"><div className="flex items-center gap-1.5"><TypeIcon className="h-3.5 w-3.5 text-primary" /><span className="text-sm font-medium">{typeLabel}</span></div></MetadataField>
              <MetadataField icon={Clock} label="Health Score"><p className="text-sm font-mono font-medium">{activeTest?.health_score ?? 0}/100</p></MetadataField>
              <MetadataField icon={Calendar} label="Timestamp"><div className="text-sm"><p>{formatDateLong(activeTest?.created_at || "")}</p><p className="text-xs text-muted-foreground">{formatTime(activeTest?.created_at || "")}</p></div></MetadataField>
              <MetadataField icon={Clock} label="Duration"><p className="text-sm font-mono font-medium">{typeof activeTest?.duration !== "undefined" ? String(activeTest?.duration) : "—"}</p></MetadataField>
              <MetadataField icon={mainStatus === "pass" ? CheckCircle2 : XCircle} label="Result"><Badge variant={mainStatus === "pass" ? "secondary" : "destructive"}>{statusLabel}</Badge></MetadataField>
            </CardContent>
          </Card>

          {aiPlan && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" />AI Plan</CardTitle>
              </CardHeader>
              <CardContent className="max-h-[16rem] space-y-2 overflow-y-auto pr-1">
                <p className="text-sm font-medium leading-relaxed">{stringifyValue(aiPlan.summary)}</p>
                <p className="text-xs text-muted-foreground whitespace-pre-wrap">{stringifyValue(aiPlan.instruction)}</p>
              </CardContent>
            </Card>
          )}

          <DashboardSection
            id="logs"
            title="Execution Logs"
            description="Raw execution logs, kept collapsed by default to preserve space."
            compact={compactMode}
            defaultOpen={sectionOpen.logs}
            open={sectionOpen.logs}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, logs: open }))}
            storageKey="test-history-detail:logs"
            className="border-slate-800 bg-[#0b1220] shadow-[0_16px_40px_rgba(2,6,23,0.18)]"
            contentClassName="p-0"
          >
            {streamLogs.length > 0 ? (
              <div className="max-h-[22rem] space-y-2 overflow-y-auto px-4 py-4 pr-2 font-mono text-sm text-slate-200">
                {visibleLogs.map((log, index) => (
                  <div key={index} className="rounded-lg border border-slate-800/80 bg-slate-950/70 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-mono text-slate-400">{log.time || ""}</p>
                      <Badge variant={log.level === "error" ? "destructive" : log.level === "warn" ? "outline" : "secondary"}>{log.level || "info"}</Badge>
                    </div>
                    <p className="mt-2 text-sm whitespace-pre-line break-words text-slate-200">{log.msg || log.message || "Log entry"}</p>
                  </div>
                ))}
                {visibleLogCount < streamLogs.length ? <button type="button" className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={() => setVisibleLogCount((current) => current + 24)}>Show more logs ({streamLogs.length - visibleLogCount})</button> : null}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-muted/10 p-6 text-sm text-muted-foreground">No execution logs captured.</div>
            )}
          </DashboardSection>

          <DashboardSection
            id="artifacts"
            title="Artifacts"
            description="Export the report, logs, or screenshot manifest."
            compact={compactMode}
            defaultOpen={sectionOpen.artifacts}
            open={sectionOpen.artifacts}
            onOpenChange={(open) => setSectionOpen((current) => ({ ...current, artifacts: open }))}
            storageKey="test-history-detail:artifacts"
            className="shadow-sm"
          >
            <div className="flex flex-wrap gap-2">
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadReport}><FileText className="mr-2 h-4 w-4" />Download Report</button>
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadLogs}><Terminal className="mr-2 h-4 w-4" />Download Logs</button>
              <button className={cn(buttonVariants({ variant: "outline", size: "sm" }))} onClick={downloadScreenshots}><FileText className="mr-2 h-4 w-4" />Download Screenshots</button>
            </div>
          </DashboardSection>

          {artifacts && Object.keys(artifacts).length > 0 && (
            <DashboardSection
              id="artifacts-preview"
              title="Artifacts Preview"
              description="Raw artifact JSON, collapsed by default."
              compact={compactMode}
              defaultOpen={sectionOpen.artifacts}
              open={sectionOpen.artifacts}
              onOpenChange={(open) => setSectionOpen((current) => ({ ...current, artifacts: open }))}
              storageKey="test-history-detail:artifacts-preview"
              className="shadow-sm"
              contentClassName="p-0"
            >
              <pre className="max-h-64 overflow-auto rounded-lg border border-border bg-muted/20 p-3 text-xs whitespace-pre-wrap break-words">{JSON.stringify(artifacts, null, 2)}</pre>
            </DashboardSection>
          )}
        </div>
      </div>
    </>
  );
}
