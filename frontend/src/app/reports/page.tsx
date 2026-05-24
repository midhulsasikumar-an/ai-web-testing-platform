"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download, Search } from "lucide-react";
import { Header } from "@/components/layout/header";
import { useAuth } from "@/context/auth-context";
import { exportAllReports, getReports, downloadReport, type ReportLibraryItem } from "@/services/reports-api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/formatters";
import { truncateText } from "@/lib/test-display";
import styles from "./report-page.module.css";

function statusLabel(status: string | undefined): string {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "pass" || normalized === "resolved" || normalized === "closed") return "Ready";
  if (normalized === "warning" || normalized === "in-progress") return "Review";
  if (normalized === "fail" || normalized === "open") return "Blocked";
  return "Ready";
}

function statusDot(status: string | undefined): string {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "pass" || normalized === "resolved" || normalized === "closed") return styles.statusDotReady;
  if (normalized === "warning" || normalized === "in-progress") return styles.statusDotReview;
  if (normalized === "fail" || normalized === "open") return styles.statusDotBlocked;
  return styles.statusDotReady;
}

function reportTag(reportType: string) {
  if (reportType === "ai") return "AI";
  if (reportType === "multi_agent") return "MULTI";
  return "LEGACY";
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
  const { isReady, token } = useAuth();
  const [reports, setReports] = useState<ReportLibraryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [reportTypeFilter, setReportTypeFilter] = useState<"all" | "legacy" | "ai" | "multi_agent">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "pass" | "warning" | "fail" | "open" | "resolved">("all");
  const [isExporting, setIsExporting] = useState(false);
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isReady || !token) {
      return;
    }

    let active = true;

    async function loadReports() {
      try {
        setLoading(true);
        const data = await getReports({}, token ?? undefined);
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
  }, [isReady, token]);

  const filteredReports = useMemo(() => {
    let result = reports;

    if (reportTypeFilter !== "all") {
      result = result.filter((item) => item.report_type === reportTypeFilter);
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
  }, [reports, reportTypeFilter, statusFilter, searchQuery]);

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
      <div className={styles.root}>
        <div className={styles.loadingWrap}>
          <div className={styles.loadingCard} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <Header title="Reports Center" description="View, analyze, and download all generated legacy, AI, and multi-agent reports." />

      <main className={styles.content}>
        <section className={styles.heroRow}>
          <div>
            <h1 className={styles.title}>Reports Center</h1>
            <p className={styles.subtitle}>View, analyze, and download all generated legacy, AI, and multi-agent reports.</p>
          </div>

          <button className={styles.exportButton} type="button" onClick={handleExportAll} disabled={isExporting || filteredReports.length === 0}>
            <Download className={styles.exportIcon} aria-hidden="true" />
            {isExporting ? "Exporting..." : "Export All"}
          </button>
        </section>

        <section className={styles.metricsGrid}>
          <article className={cn(styles.metricCard, styles.metricAccentBlue)}>
            <div className={styles.metricLabel}>Total Reports</div>
            <div className={styles.metricValue}>{totalReports}</div>
          </article>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Legacy Reports</div>
            <div className={styles.metricValue}>{legacyReports}</div>
          </article>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>AI Reports</div>
            <div className={styles.metricValue}>{aiReports}</div>
          </article>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Multi-Agent</div>
            <div className={styles.metricValue}>{multiAgentReports}</div>
          </article>
          <article className={cn(styles.metricCard, styles.metricAccentPurple)}>
            <div className={styles.metricLabel}>This Week</div>
            <div className={styles.metricValue}>{thisWeek}</div>
          </article>
        </section>

        <section className={styles.filterRow}>
          <div className={styles.tableSearch}>
            <Search className={styles.tableSearchIcon} aria-hidden="true" />
            <input
              className={styles.tableSearchInput}
              placeholder="Search reports by test name, website, or type..."
              aria-label="Search reports by test name, website, or type"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>

          <div className={styles.chips}>
            <button type="button" className={cn(styles.chip, reportTypeFilter === "all" && styles.chipActive)} onClick={() => setReportTypeFilter("all")}>All</button>
            <button type="button" className={cn(styles.chip, reportTypeFilter === "legacy" && styles.chipActive)} onClick={() => setReportTypeFilter("legacy")}>Legacy</button>
            <button type="button" className={cn(styles.chip, reportTypeFilter === "ai" && styles.chipActive)} onClick={() => setReportTypeFilter("ai")}>AI</button>
            <button type="button" className={cn(styles.chip, reportTypeFilter === "multi_agent" && styles.chipActive)} onClick={() => setReportTypeFilter("multi_agent")}>Multi-Agent</button>
            <button type="button" className={cn(styles.chip, statusFilter === "fail" && styles.chipActive)} onClick={() => setStatusFilter(statusFilter === "fail" ? "all" : "fail")}>Failed Tests</button>
            <button type="button" className={cn(styles.chip, statusFilter === "open" && styles.chipActive)} onClick={() => setStatusFilter(statusFilter === "open" ? "all" : "open")}>Open Bugs</button>
          </div>
        </section>

        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <div>Test Name</div>
            <div>Report Type</div>
            <div>Website</div>
            <div>Generated Date</div>
            <div>Status</div>
            <div>Score</div>
            <div>Actions</div>
          </div>

          <div className={styles.tableBody}>
            {filteredReports.map((report) => (
              <div key={report.report_id} className={styles.tableRow}>
                <div className={styles.reportNameCell}>
                  <div className={styles.reportIcon} aria-hidden="true" />
                  <div>
                    <div className={styles.reportName}>{truncateText(report.test_name, 80)}</div>
                    <div className={styles.reportSubtle}>{reportTag(report.report_type)}</div>
                  </div>
                </div>

                <div>
                  <span className={styles.typeBadge}>{reportTag(report.report_type)}</span>
                </div>

                <div className={styles.websiteCell}>{report.website}</div>

                <div className={styles.generatedCell}>{formatDate(report.generated_date ?? "")}</div>

                <div className={styles.statusCell}>
                  <span className={cn(styles.statusDot, statusDot(report.status))} />
                  <span>{statusLabel(report.status)}</span>
                </div>

                <div className={styles.scoreCell}>{report.score ?? "-"}</div>

                <div className={styles.actionsCell}>
                  {report.related_bug_id || report.related_test_id ? (
                    <Link
                      href={report.related_bug_id ? `/bugs/${report.related_bug_id}` : `/test-history/${report.related_test_id}`}
                      className={styles.actionLink}
                    >
                      View
                    </Link>
                  ) : (
                    <span className={styles.reportSubtle}>N/A</span>
                  )}
                  <span className={styles.actionDivider}>|</span>
                  <button type="button" className={styles.actionButton} onClick={() => handleDownload(report)} disabled={downloadingReportId === report.report_id}>
                    {downloadingReportId === report.report_id ? "Downloading..." : "Download"}
                  </button>
                </div>
              </div>
            ))}
            {filteredReports.length === 0 ? (
              <div className={styles.tableRow}>
                <div className={styles.reportSubtle}>No reports found for the current filters.</div>
                <div />
                <div />
                <div />
                <div />
                <div />
                <div />
              </div>
            ) : null}
          </div>
        </section>
      </main>
    </div>
  );
}
