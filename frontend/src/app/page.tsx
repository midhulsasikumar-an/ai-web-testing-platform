"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/dashboard/stat-card";
import { TestActivityChart } from "@/components/dashboard/test-activity-chart";
import { BugDistributionChart } from "@/components/dashboard/bug-distribution-chart";
import { AILogSummary } from "@/components/dashboard/ai-log-summary";
import { SystemHealth } from "@/components/dashboard/system-health";
import { RecentBugs } from "@/components/dashboard/recent-bugs";
import { useDashboardStore } from "@/store/dashboard-store";
import { useBugsStore } from "@/store/bugs-store";
import { FlaskConical, CheckCircle2, XCircle, Bug, Loader2 } from "lucide-react";
import { LandingLogin } from "@/components/auth/landing-login";

export default function DashboardPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  
  const { stats, loading: statsLoading, fetchStats } = useDashboardStore();
  const { bugs, loading: bugsLoading, fetchBugs } = useBugsStore();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setIsAuthenticated(false);
    } else {
      setIsAuthenticated(true);
      fetchStats();
      fetchBugs();
    }
  }, [router, fetchStats, fetchBugs]);

  if (isAuthenticated === null) return null; // Wait for auth check

  if (!isAuthenticated) {
    return <LandingLogin />;
  }

  if (statsLoading || bugsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <Header
        title="Dashboard"
        description="Overview of your testing activity, bug reports, and system health."
      />

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tests"
          value={stats?.totalTests || 0}
          icon={FlaskConical}
          trend="+12% from last week"
          trendUp={true}
          accentColor="bg-blue-500"
        />
        <StatCard
          title="Passed"
          value={stats?.passed || 0}
          icon={CheckCircle2}
          trend={`${(stats?.totalTests || 0) > 0 ? Math.round(((stats?.passed || 0) / stats!.totalTests) * 100) : 0}% pass rate`}
          trendUp={true}
          accentColor="bg-green-500"
        />
        <StatCard
          title="Failed"
          value={stats?.failed || 0}
          icon={XCircle}
          trend={`${(stats?.totalTests || 0) > 0 ? Math.round(((stats?.failed || 0) / stats!.totalTests) * 100) : 0}% fail rate`}
          trendUp={false}
          accentColor="bg-red-500"
        />
        <StatCard
          title="Active Bugs"
          value={stats?.openBugs || 0}
          icon={Bug}
          trend="Needs attention"
          accentColor="bg-amber-500"
        />
      </div>

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <TestActivityChart />
        <BugDistributionChart />
      </div>

      {/* AI Log + System Health */}
      <div className="grid gap-4 lg:grid-cols-3">
        <AILogSummary />
        <SystemHealth />
      </div>

      {/* Recent bugs */}
      <RecentBugs bugs={bugs} />
    </>
  );
}