"use client";

import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/dashboard/stat-card";
import { TestActivityChart } from "@/components/dashboard/test-activity-chart";
import { BugDistributionChart } from "@/components/dashboard/bug-distribution-chart";
import { AILogSummary } from "@/components/dashboard/ai-log-summary";
import { SystemHealth } from "@/components/dashboard/system-health";
import { RecentBugs } from "@/components/dashboard/recent-bugs";
import { useAuth } from "@/context/auth-context";
import { FlaskConical, CheckCircle2, XCircle, Bug } from "lucide-react";
import { useEffect, useState } from "react";
import { getDashboardStats, DashboardStatsResponse } from "@/services/dashboard-api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const { isReady, token } = useAuth();

  useEffect(() => {
    if (!isReady || !token) {
      return;
    }

    async function loadStats() {
      try {
        setLoading(true);
        const data = await getDashboardStats(token ?? undefined);
        setStats(data);
      } catch (err) {
        if (err instanceof Error && err.message.includes("401 Unauthorized")) {
          setStats(null);
          return;
        }

        console.error("Failed to load dashboard stats", err);
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, [isReady, token]);

  if (!isReady || !token) {
    return <div>Loading dashboard...</div>;
  }

  if (loading || !stats) {
    return <div>Loading dashboard...</div>;
  }

  return (
    <>
      <Header
        title="Dashboard"
        description="Overview of your testing activity, bug reports, and system health."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tests"
          value={stats?.total_tests ?? 0}
          icon={FlaskConical}
          trend="+12% from last week"
          trendUp={true}
          accentColor="bg-blue-500"
        />
        <StatCard
          title="Passed"
          value={stats?.passed ?? 0}
          icon={CheckCircle2}
          trend={`${
            stats?.total_tests
              ? Math.round(((stats?.passed ?? 0) / stats.total_tests) * 100)
              : 0
          }% pass rate`}
          trendUp={true}
          accentColor="bg-green-500"
        />

        <StatCard
          title="Failed"
          value={stats?.failed ?? 0}
          icon={XCircle}
          trend={`${
            stats?.total_tests
              ? Math.round(((stats?.failed ?? 0) / stats.total_tests) * 100)
              : 0
          }% fail rate`}
          trendUp={false}
          accentColor="bg-red-500"
        />
        <StatCard
          title="Active Bugs"
          value={stats?.open_bugs ?? 0}
          icon={Bug}
          trend="Needs attention"
          accentColor="bg-amber-500"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <TestActivityChart data={stats.test_activity} />

        <BugDistributionChart
          data={stats.bug_distribution}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <AILogSummary aiLogs={stats?.ai_logs} />
        <SystemHealth
          averageHealth={stats.average_health}
        />
      </div>

      <RecentBugs tests={stats.recent_tests} />
    </>
  );
}
