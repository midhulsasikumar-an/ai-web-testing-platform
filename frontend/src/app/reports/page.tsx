"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download, Search, FileText, ExternalLink, Globe, Calendar } from "lucide-react";
import { Header } from "@/components/layout/header";
import { useAuth } from "@/context/auth-context";
import { exportAllReports, getReports, downloadReport, type ReportLibraryItem } from "@/services/reports-api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/formatters";
import { truncateText } from "@/lib/test-display";
import { Card, CardContent } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";

function statusLabel(status: string | undefined): string {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "pass" || normalized === "resolved" || normalized === "closed") return "Ready";
  if (normalized === "warning" || normalized === "in-progress") return "Review";
  if (normalized === "fail" || normalized === "open") return "Blocked";
  return "Ready";
}

function statusDot(status: string | undefined): string {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "pass" || normalized === "resolved" || normalized === "closed") return "bg-emerald-500";
  if (normalized === "warning" || normalized === "in-progress") return "bg-amber-500";
  if (normalized === "fail" || normalized === "open") return "bg-red-500";
  return "bg-emerald-500";
}

function reportTag(reportType: string) {
  if (reportType === "ai") return "AI";
  if (reportType === "multi_agent") return "MULTI";
  return "LEGACY";
}

function getReportTypeLabel(report: ReportLibraryItem): string {
  return report.report_label || reportTag(report.report_type);
}

function isBugReport(report: ReportLibraryItem): boolean {
  return Boolean(report.related_bug_id) && !report.related_test_id;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const { isReady } = useAuth();
  const [reports, setReports] = useState<ReportLibraryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [reportTypeFilter, setReportTypeFilter] = useState<"all" | "legacy" | "ai" | "multi_agent">("all");
  const [reportKindFilter, setReportKindFilter] = useState<"all" | "test" | "bug">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "pass" | "warning" | "fail" | "open" | "resolved">("all");
  const [isExporting, setIsExporting] = useState(false);
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    let active = true;

    async function loadReports() {
      try {
        setLoading(true);
        const data = await getReports({});
        if (active) {
          setReports(data.items || []);
        }
      } catch (error) {
        console.error("Failed to load reports", error);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadReports();
    return () => {
      active = false;
    };
  }, [isReady]);

  const filteredReports = useMemo(() => {
    let result = reports;

    if (reportTypeFilter !== "all") {
      result = result.filter((item) => item.report_type === reportTypeFilter);
    }

    if (reportKindFilter === "test") {
      result = result.filter((item) => !isBugReport(item));
    } else if (reportKindFilter === "bug") {
      result = result.filter((item) => isBugReport(item));
    }

    if (statusFilter !== "all") {
      result = result.filter((item) => String(item.status || "").toLowerCase() === statusFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (item) =>
          item.test_name.toLowerCase().includes(query) ||
          item.website.toLowerCase().includes(query) ||
          item.report_type.toLowerCase().includes(query)
      );
    }

    return result;
  }, [reports, reportTypeFilter, reportKindFilter, statusFilter, searchQuery]);

  const totalReports = reports.length;
  const legacyReports = reports.filter((item) => item.report_type === "legacy").length;
  const aiReports = reports.filter((item) => item.report_type === "ai").length;
  const multiAgentReports = reports.filter((item) => item.report_type === "multi_agent").length;
  const thisWeek = reports.filter((item) => {
    const generatedAt = new Date(item.generated_date).getTime();
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    return !Number.isNaN(generatedAt) && generatedAt >= weekAgo;
  }).length;

  async function handleDownload(item: ReportLibraryItem) {
    try {
      setDownloadingReportId(item.report_id);
      const blob = await downloadReport(item.report_id);
      const filename = `${item.report_type}-${item.test_name.replace(/\s+/g, "-").toLowerCase()}.pdf`;
      downloadBlob(blob, filename);
    } catch (error) {
      console.error("Failed to download report", error);
    } finally {
      setDownloadingReportId(null);
    }
  }

  async function handleExportAll() {
    try {
      setIsExporting(true);
      const blob = await exportAllReports({
        q: searchQuery || undefined,
        reportType: reportTypeFilter,
        status: statusFilter,
      });
      downloadBlob(blob, "reports-export.zip");
    } catch (error) {
      console.error("Failed to export reports", error);
    } finally {
      setIsExporting(false);
    }
  }

  if (!isReady || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Reports Center"
        description="View, analyze, and download all generated legacy, AI, and multi-agent reports."
        actions={
          <button
            type="button"
            onClick={handleExportAll}
            disabled={isExporting || filteredReports.length === 0}
            className={cn(
              buttonVariants({ variant: "default", size: "sm" }),
              "h-8"
            )}
          >
            <Download className="h-3.5 w-3.5" />
            {isExporting ? "Exporting..." : "Export All"}
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <SummaryStat label="Total Reports" value={totalReports} accent="blue" />
        <SummaryStat label="Legacy" value={legacyReports} accent="slate" />
        <SummaryStat label="AI / Multi-Agent" value={aiReports + multiAgentReports} accent="indigo" />
        <SummaryStat label="This Week" value={thisWeek} accent="emerald" />
      </div>

      <Card>
        <CardContent className="space-y-3.5 p-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-8 pr-3 text-[13px] text-slate-700 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/10"
              placeholder="Search reports by test name, website, or type..."
              aria-label="Search reports by test name, website, or type"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Chip active={reportKindFilter === "all"} onClick={() => setReportKindFilter("all")}>All Kinds</Chip>
            <Chip active={reportKindFilter === "test"} onClick={() => setReportKindFilter("test")}>Test Reports</Chip>
            <Chip active={reportKindFilter === "bug"} onClick={() => setReportKindFilter("bug")}>Bug Reports</Chip>
            <div className="mx-1 h-4 w-px bg-slate-200" />
            <Chip active={reportTypeFilter === "legacy"} onClick={() => setReportTypeFilter(reportTypeFilter === "legacy" ? "all" : "legacy")}>Legacy</Chip>
            <Chip active={reportTypeFilter === "ai"} onClick={() => setReportTypeFilter(reportTypeFilter === "ai" ? "all" : "ai")}>AI</Chip>
            <Chip active={reportTypeFilter === "multi_agent"} onClick={() => setReportTypeFilter(reportTypeFilter === "multi_agent" ? "all" : "multi_agent")}>Multi-Agent</Chip>
            <div className="mx-1 h-4 w-px bg-slate-200" />
            <Chip active={statusFilter === "fail"} onClick={() => setStatusFilter(statusFilter === "fail" ? "all" : "fail")}>Failed Tests</Chip>
            <Chip active={statusFilter === "open"} onClick={() => setStatusFilter(statusFilter === "open" ? "all" : "open")}>Open Bugs</Chip>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {filteredReports.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
              <FileText className="h-8 w-8 text-slate-300" />
              <p className="text-[13px] font-medium text-slate-500">No reports found for the current filters.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredReports.map((report) => {
                const bugReport = isBugReport(report);
                return (
                  <div
                    key={report.report_id}
                    className="grid grid-cols-12 items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50/60"
                  >
                    <div className="col-span-12 flex items-center gap-2.5 min-w-0 md:col-span-4">
                      <div className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                        bugReport ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"
                      )}>
                        <FileText className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-semibold text-slate-900">
                          {truncateText(report.test_name, 60)}
                        </p>
                        <p className="truncate text-[11.5px] text-slate-500">
                          {report.report_label || getReportTypeLabel(report)}
                        </p>
                      </div>
                    </div>

                    <div className="col-span-6 hidden items-center gap-1.5 md:col-span-2 md:flex">
                      <span className={cn(
                        "rounded-md border px-1.5 py-0.5 text-[10px] font-bold",
                        bugReport
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-blue-200 bg-blue-50 text-blue-700"
                      )}>
                        {bugReport ? "BUG" : "TEST"}
                      </span>
                    </div>

                    <div className="col-span-6 hidden items-center gap-1.5 md:col-span-2 md:flex">
                      <span className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                        {getReportTypeLabel(report)}
                      </span>
                      <span className="truncate text-[11.5px] text-slate-500">{report.test_type || "full"}</span>
                    </div>

                    <div className="col-span-6 hidden items-center gap-1.5 truncate md:col-span-2 md:flex">
                      <Globe className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="truncate text-[12px] text-slate-700">{report.website}</span>
                    </div>

                    <div className="col-span-6 hidden items-center gap-1.5 md:col-span-1 md:flex">
                      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", statusDot(report.status))} />
                      <span className="text-[11.5px] font-medium text-slate-700">{statusLabel(report.status)}</span>
                    </div>

                    <div className="col-span-12 flex items-center justify-end gap-1.5 md:col-span-1">
                      <Link
                        href={`/reports/${report.report_id}`}
                        className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-700 transition-colors hover:bg-slate-50"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Open
                      </Link>
                      <button
                        type="button"
                        className="inline-flex h-7 items-center gap-1 rounded-md bg-slate-900 px-2 text-[11.5px] font-medium text-white transition-colors hover:bg-slate-800 disabled:opacity-60"
                        onClick={() => handleDownload(report)}
                        disabled={downloadingReportId === report.report_id}
                      >
                        <Download className="h-3 w-3" />
                        {downloadingReportId === report.report_id ? "…" : "PDF"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-7 items-center rounded-full border px-2.5 text-[11.5px] font-medium transition-colors",
        active
          ? "border-slate-900 bg-slate-900 text-white"
          : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
      )}
    >
      {children}
    </button>
  );
}

function SummaryStat({ label, value, accent }: { label: string; value: number; accent: "blue" | "indigo" | "emerald" | "slate" }) {
  const accentMap: Record<typeof accent, string> = {
    blue: "text-blue-600 bg-blue-50",
    indigo: "text-indigo-600 bg-indigo-50",
    emerald: "text-emerald-600 bg-emerald-50",
    slate: "text-slate-600 bg-slate-100",
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs-token">
      <div className="flex items-center justify-between">
        <span className="text-eyebrow">{label}</span>
        <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-bold", accentMap[accent])}>
          {value}
        </span>
      </div>
      <p className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">{value.toLocaleString()}</p>
    </div>
  );
}
