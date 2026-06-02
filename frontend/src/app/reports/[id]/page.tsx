"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Copy,
  Download,
  LayoutDashboard,
  Layers3,
  MessageSquareQuote,
} from "lucide-react";

import { Header } from "@/components/layout/header";
import { DashboardSection } from "@/components/shared/dashboard-section";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/context/auth-context";
import { cn } from "@/lib/utils";
import { createReportExport, downloadReportExport, getReportById, type ReportLibraryItem } from "@/services/reports-api";

function profileLabel(value: string | null | undefined): string {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "smoke") return "Smoke";
  if (normalized === "standard") return "Standard";
  if (normalized === "deep") return "Deep";
  if (normalized === "exhaustive") return "Exhaustive";
  return value || "Standard";
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

function downloadBlob(filename: string, blob: Blob): void {
  if (typeof window === "undefined") return;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export default function ReportDetailPage() {
  const { isReady } = useAuth();
  const params = useParams();
  const reportId = String(params.id || "");
  const [report, setReport] = useState<ReportLibraryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [denseMode, setDenseMode] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");
  const [exportingFormat, setExportingFormat] = useState<"pdf" | "json" | "markdown" | "csv" | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem("report-detail:dense-mode");
    setDenseMode(saved === "1");
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("report-detail:dense-mode", denseMode ? "1" : "0");
  }, [denseMode]);

  useEffect(() => {
    if (!isReady || !reportId) return;

    let active = true;
    setLoading(true);
    getReportById(reportId)
      .then((data) => {
        if (!active) return;
        setReport(data);
      })
      .catch((error) => {
        console.error("Failed to load report detail", error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isReady, reportId]);

  const objectiveCoverage = useMemo(() => {
    return Array.isArray(report?.objective_coverage) ? report.objective_coverage : [];
  }, [report]);

  const riskSummary = useMemo(() => {
    return report?.risk_summary && typeof report.risk_summary === "object" ? report.risk_summary as Record<string, unknown> : null;
  }, [report]);

  const overviewStats = [
    { label: "Objectives", value: objectiveCoverage.length },
    { label: "Coverage Groups", value: objectiveCoverage.length },
    { label: "Health Score", value: report?.score ?? "-" },
    { label: "Report Type", value: report?.report_type ?? "-" },
  ];

  const handleCopyLink = async () => {
    if (typeof window === "undefined") return;
    try {
      await window.navigator.clipboard.writeText(window.location.href);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1500);
    } catch (error) {
      console.error("Failed to copy report link", error);
    }
  };

  const handleExport = async (format: "pdf" | "json" | "markdown" | "csv") => {
    if (!reportId) return;

    try {
      setExportingFormat(format);
      const record = await createReportExport(
        reportId,
        {
          format,
          includeScreenshots: format === "pdf",
          includeComparison: false,
          title: `${report?.test_name || "Report"} (${format.toUpperCase()})`,
        },
      );
      const blob = await downloadReportExport(reportId, record.export_id);
      const extension = format === "markdown" ? "md" : format;
      downloadBlob(`${(report?.test_name || "report").replace(/[^a-z0-9-_]+/gi, "-").toLowerCase()}-${format}.${extension}`, blob);
    } catch (error) {
      console.error(`Failed to export report as ${format}`, error);
    } finally {
      setExportingFormat(null);
    }
  };

  if (!isReady || loading) {
    return <div className="p-8 text-sm text-slate-500">Loading report...</div>;
  }

  if (!report) {
    return <div className="p-8 text-sm text-slate-500">Report not found.</div>;
  }

  return (
    <>
      <Header title="Report Detail" eyebrow="Results">
        <Link href="/reports" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Reports
        </Link>
      </Header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px] items-start">
        <div className="min-w-0 space-y-6">
          <Card className="border-border shadow-sm">
            <CardContent className="space-y-5 pt-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={String(report.status || "").toLowerCase() === "completed" ? "secondary" : "outline"}>{report.status}</Badge>
                    <Badge variant="outline">{profileLabel(report.test_type)}</Badge>
                    <Badge variant="outline">{report.report_type}</Badge>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">{report.test_name}</h1>
                    <p className="mt-1 max-w-3xl break-words text-sm text-slate-500">{report.website}</p>
                  </div>
                  <p className="max-w-3xl text-sm leading-relaxed text-slate-600">
                    {report.report_label ? `${report.report_label}. ` : ""}
                    {report.related_test_id ? `Related test: ${report.related_test_id}. ` : ""}
                    {report.related_bug_id ? `Related bug: ${report.related_bug_id}.` : ""}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button type="button" onClick={() => setDenseMode((current) => !current)} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                    <LayoutDashboard className="mr-2 h-4 w-4" />
                    {denseMode ? "Expanded" : "Compact"}
                  </button>
                  <button type="button" onClick={handleCopyLink} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                    <Copy className="mr-2 h-4 w-4" />
                    {copyState === "copied" ? "Copied" : "Copy Link"}
                  </button>
                  <button type="button" onClick={() => handleExport("pdf")} disabled={exportingFormat !== null} className={cn(buttonVariants({ size: "sm" }))}>
                    <Download className="mr-2 h-4 w-4" />
                    {exportingFormat === "pdf" ? "Exporting..." : "Export PDF"}
                  </button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {overviewStats.map((item) => (
                  <div key={item.label} className="rounded-lg border border-border bg-white p-4">
                    <p className="text-eyebrow">{item.label}</p>
                    <p className="mt-2 break-words text-xl font-semibold text-slate-900">{String(item.value)}</p>
                  </div>
                ))}
              </div>

              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                <button type="button" onClick={() => handleExport("json")} disabled={exportingFormat !== null} className={cn(buttonVariants({ variant: "outline", size: "sm" }), "justify-start")}>
                  <Download className="mr-2 h-4 w-4" />
                  {exportingFormat === "json" ? "Exporting JSON..." : "Export JSON"}
                </button>
                <button type="button" onClick={() => handleExport("markdown")} disabled={exportingFormat !== null} className={cn(buttonVariants({ variant: "outline", size: "sm" }), "justify-start")}>
                  <MessageSquareQuote className="mr-2 h-4 w-4" />
                  {exportingFormat === "markdown" ? "Exporting Markdown..." : "Export Markdown"}
                </button>
                <button type="button" onClick={() => handleExport("csv")} disabled={exportingFormat !== null} className={cn(buttonVariants({ variant: "outline", size: "sm" }), "justify-start")}>
                  <Layers3 className="mr-2 h-4 w-4" />
                  {exportingFormat === "csv" ? "Exporting CSV..." : "Export CSV"}
                </button>
              </div>
            </CardContent>
          </Card>

          <DashboardSection
            id="overview"
            title="Execution Overview"
            description="High-level report summary, routing context, and key signals."
            compact={denseMode}
            storageKey="report-detail:overview"
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-lg border border-border bg-slate-50 p-4">
                <p className="text-eyebrow">Generated</p>
                <p className="mt-2 break-words text-sm font-medium text-slate-900">{report.generated_date}</p>
              </div>
              <div className="rounded-lg border border-border bg-slate-50 p-4">
                <p className="text-eyebrow">Related Test</p>
                <p className="mt-2 break-words text-sm font-medium text-slate-900">{report.related_test_id || "-"}</p>
              </div>
              <div className="rounded-lg border border-border bg-slate-50 p-4">
                <p className="text-eyebrow">Related Bug</p>
                <p className="mt-2 break-words text-sm font-medium text-slate-900">{report.related_bug_id || "-"}</p>
              </div>
            </div>
          </DashboardSection>

          <DashboardSection
            id="objective-coverage"
            title="Objective Coverage"
            description="Coverage breadth, execution counts, and objective health."
            compact={denseMode}
            storageKey="report-detail:objective-coverage"
          >
            <div className="space-y-3">
              {objectiveCoverage.length > 0 ? (
                objectiveCoverage.map((objective, index) => {
                  const scenarios = Array.isArray(objective.scenarios) ? (objective.scenarios as Record<string, unknown>[]) : [];
                  return (
                    <div key={`${String(objective.objective_id || index)}`} className="rounded-lg border border-border bg-white">
                      <div className="flex flex-col gap-2 border-b border-border bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="font-semibold text-slate-900">{String(objective.objective_name || objective.feature_name || `Objective ${index + 1}`)}</p>
                          <p className="text-muted-sm">{profileLabel(String(objective.coverage_profile || objective.coverage_level || ""))} coverage</p>
                        </div>
                        <Badge variant={String(objective.execution_status || "").toLowerCase() === "completed" ? "secondary" : "outline"}>
                          {String(objective.execution_status || "pending")}
                        </Badge>
                      </div>

                      <div className="grid gap-3 px-4 py-4 text-sm sm:grid-cols-4">
                        <div className="rounded-lg border border-border bg-slate-50 px-3 py-2">
                          <p className="text-eyebrow">Scenarios</p>
                          <p className="mt-1 font-semibold text-slate-900">{String(objective.generated_scenarios ?? 0)}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-slate-50 px-3 py-2">
                          <p className="text-eyebrow">Steps</p>
                          <p className="mt-1 font-semibold text-slate-900">{String(objective.generated_steps ?? 0)}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-slate-50 px-3 py-2">
                          <p className="text-eyebrow">Passed</p>
                          <p className="mt-1 font-semibold text-emerald-600">{String(objective.passed_steps ?? 0)}</p>
                        </div>
                        <div className="rounded-lg border border-border bg-slate-50 px-3 py-2">
                          <p className="text-eyebrow">Failed</p>
                          <p className="mt-1 font-semibold text-red-600">{String(objective.failed_steps ?? 0)}</p>
                        </div>
                      </div>

                      {scenarios.length > 0 ? (
                        <div className="space-y-2 px-4 pb-4">
                          {scenarios.map((scenario, scenarioIndex) => (
                            <div key={`${String(scenario.scenario_id || scenarioIndex)}`} className="rounded-lg border border-border bg-slate-50 px-3 py-2 text-sm">
                              <div className="flex items-center justify-between gap-2">
                                <p className="font-medium text-slate-900">{String(scenario.scenario_name || `Scenario ${scenarioIndex + 1}`)}</p>
                                <Badge variant={String(scenario.execution_status || "").toLowerCase() === "completed" ? "secondary" : "outline"}>
                                  {String(scenario.execution_status || "pending")}
                                </Badge>
                              </div>
                              <p className="mt-1 text-muted-sm">
                                Steps: {String(scenario.generated_steps ?? 0)} | Passed: {String(scenario.passed_steps ?? 0)} | Failed: {String(scenario.failed_steps ?? 0)}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              ) : (
                <div className="rounded-lg border border-dashed border-border bg-slate-50 p-6 text-sm text-slate-500">No objective coverage available.</div>
              )}
            </div>
          </DashboardSection>

          <DashboardSection
            id="risk-summary"
            title="Risk Summary"
            description="Aggregated risk signals captured for this report."
            compact={denseMode}
            storageKey="report-detail:risk-summary"
          >
            {riskSummary ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {Object.entries(riskSummary)
                  .filter(([, value]) => Boolean(value))
                  .map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-border bg-slate-50 px-3 py-3 text-sm">
                      <p className="text-eyebrow">{key.replace(/_/g, " ")}</p>
                      <p className="mt-2 break-words font-semibold text-slate-900">{String(value)}</p>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-slate-50 p-6 text-sm text-slate-500">No risk summary available for this run.</div>
            )}
          </DashboardSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-20">
          <Card className="border-border">
            <CardContent className="space-y-4 py-4">
              <div className="grid gap-3 rounded-lg border border-border bg-slate-50 p-4">
                <div>
                  <p className="text-eyebrow">Summary</p>
                  <p className="mt-2 text-sm leading-relaxed text-slate-700">{stringifyValue(report.summary || report.test_name || "No summary available.")}</p>
                </div>

                <div className="rounded-lg border border-border bg-white p-3 text-sm">
                  <p className="text-eyebrow">Website</p>
                  <p className="mt-1 break-all text-slate-900">{report.website}</p>
                </div>

                <div className="rounded-lg border border-border bg-white p-3 text-sm">
                  <p className="text-eyebrow">Related IDs</p>
                  <p className="mt-1 break-words text-slate-900">{report.related_test_id || report.related_bug_id || "-"}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </>
  );
}