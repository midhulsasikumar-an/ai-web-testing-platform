"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download, Search, Sparkles } from "lucide-react";
import { Header } from "@/components/layout/header";
import { useAuth } from "@/context/auth-context";
import { getDashboardStats, type DashboardStatsResponse, type RecentTest } from "@/services/dashboard-api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/formatters";
import styles from "./report-page.module.css";

function statusLabel(status: string | undefined): string {
  if (status === "pass") return "Ready";
  if (status === "warning") return "Review";
  if (status === "fail") return "Blocked";
  return "Ready";
}

function statusDot(status: string | undefined): string {
  if (status === "pass") return styles.statusDotReady;
  if (status === "warning") return styles.statusDotReview;
  if (status === "fail") return styles.statusDotBlocked;
  return styles.statusDotReady;
}

function reportTag(testType: string) {
  return testType === "bug" ? "BUG" : "TEST";
}

export default function ReportsPage() {
  const { isReady, token } = useAuth();
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isReady || !token) {
      return;
    }

    let active = true;

    async function loadReports() {
      try {
        setLoading(true);
        const data = await getDashboardStats(token ?? undefined);
        if (active) {
          setStats(data);
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

  const reports = useMemo(() => (stats?.recent_tests ?? []).slice(0, 3), [stats]);
  const totalReports = stats?.total_tests ?? 0;
  const testReports = stats?.passed ?? 0;
  const bugReports = stats?.open_bugs ?? 0;
  const thisWeek = reports.length;

  if (!isReady || loading || !stats) {
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
      <Header title="Reports Center" description="View, analyze, and download all generated test and bug reports." />

      <main className={styles.content}>
        <section className={styles.heroRow}>
          <div>
            <h1 className={styles.title}>Reports Center</h1>
            <p className={styles.subtitle}>View, analyze, and download all generated test and bug reports.</p>
          </div>

          <button className={styles.exportButton} type="button">
            <Download className={styles.exportIcon} aria-hidden="true" />
            Export All
          </button>
        </section>

        <section className={styles.metricsGrid}>
          <article className={cn(styles.metricCard, styles.metricAccentBlue)}>
            <div className={styles.metricLabel}>Total Reports</div>
            <div className={styles.metricValue}>{totalReports}</div>
          </article>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Test Reports</div>
            <div className={styles.metricValue}>{testReports}</div>
          </article>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Bug Reports</div>
            <div className={styles.metricValue}>{bugReports}</div>
          </article>
          <article className={cn(styles.metricCard, styles.metricAccentPurple)}>
            <div className={styles.metricLabel}>This Week</div>
            <div className={styles.metricValue}>{thisWeek}</div>
          </article>
        </section>

        <section className={styles.filterRow}>
          <div className={styles.tableSearch}>
            <Search className={styles.tableSearchIcon} aria-hidden="true" />
            <input className={styles.tableSearchInput} placeholder="Search reports by name or website ..." aria-label="Search reports by name or website" />
          </div>

          <div className={styles.chips}>
            { ["All", "Test Reports", "Bug Reports", "Recent", "Failed Tests", "High Priority Bugs"].map((chip, index) => (
              <button key={chip} type="button" className={cn(styles.chip, index === 0 && styles.chipActive)}>
                {chip}
              </button>
            ))}
          </div>
        </section>

        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <div>Report Name</div>
            <div>Type</div>
            <div>Website</div>
            <div>Generated On</div>
            <div>Status</div>
            <div>Score</div>
            <div>Actions</div>
          </div>

          <div className={styles.tableBody}>
            {reports.map((test: RecentTest) => (
              <div key={test.test_id} className={styles.tableRow}>
                <div className={styles.reportNameCell}>
                  <div className={styles.reportIcon} aria-hidden="true" />
                  <div>
                    <div className={styles.reportName}>{test.project}</div>
                    <div className={styles.reportSubtle}>{reportTag(test.test_type)}</div>
                  </div>
                </div>

                <div>
                  <span className={styles.typeBadge}>{test.test_type.toUpperCase()}</span>
                </div>

                <div className={styles.websiteCell}>{test.url}</div>

                <div className={styles.generatedCell}>{formatDate(test.date ?? "")}</div>

                <div className={styles.statusCell}>
                  <span className={cn(styles.statusDot, statusDot(test.overall_status))} />
                  <span>{statusLabel(test.overall_status)}</span>
                </div>

                <div className={styles.scoreCell}>{test.health_score}/100</div>

                <div className={styles.actionsCell}>
                  <Link href={`/test-history/${test.test_id}`} className={styles.actionLink}>
                    View
                  </Link>
                  <span className={styles.actionDivider}>|</span>
                  <button type="button" className={styles.actionButton}>
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
