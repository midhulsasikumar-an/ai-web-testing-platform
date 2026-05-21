"use client";

import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/dashboard/stat-card";
import { TestActivityChart } from "@/components/dashboard/test-activity-chart";
import { BugDistributionChart } from "@/components/dashboard/bug-distribution-chart";
import { SystemHealth } from "@/components/dashboard/system-health";
import { RecentBugs } from "@/components/dashboard/recent-bugs";
import { useAuth } from "@/context/auth-context";
import { getDashboardStats, type DashboardStatsResponse } from "@/services/dashboard-api";
import { FlaskConical, CheckCircle2, XCircle, Bug } from "lucide-react";
import { useEffect, useState } from "react";

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

  if (!isReady || !token || loading || !stats) {
    return <div>Loading reports...</div>;
  }

  return (
    <>
      <Header
        title="Reports"
        description="Analytics and saved report summaries for your test runs and bug trends."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tests"
          value={stats.total_tests}
          icon={FlaskConical}
          trend="From the latest dashboard snapshot"
          trendUp={true}
          accentColor="bg-blue-500"
        />
        <StatCard
          title="Passed"
          value={stats.passed}
          icon={CheckCircle2}
          trend="Green health signals"
          trendUp={true}
          accentColor="bg-green-500"
        />
        <StatCard
          title="Failed"
          value={stats.failed}
          icon={XCircle}
          trend="Issues requiring review"
          trendUp={false}
          accentColor="bg-red-500"
        />
        <StatCard
          title="Active Bugs"
          value={stats.open_bugs}
          icon={Bug}
          trend="Open items from test runs"
          accentColor="bg-amber-500"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <TestActivityChart data={stats.test_activity} />
        <BugDistributionChart data={stats.bug_distribution} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SystemHealth averageHealth={stats.average_health} />
        <RecentBugs tests={stats.recent_tests} />
      </div>
    </>
  );
}
