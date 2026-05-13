"use client";

import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/dashboard/stat-card";
import { TestActivityChart } from "@/components/dashboard/test-activity-chart";
import { BugDistributionChart } from "@/components/dashboard/bug-distribution-chart";
import { AILogSummary } from "@/components/dashboard/ai-log-summary";
import { SystemHealth } from "@/components/dashboard/system-health";
import { RecentBugs } from "@/components/dashboard/recent-bugs";
import { useBugContext } from "@/context/bug-context";
import { FlaskConical, CheckCircle2, XCircle, Bug } from "lucide-react";

export default function DashboardPage() {
  const { testResults, stats } = useBugContext();

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
          value={stats.totalTests}
          icon={FlaskConical}
          trend="+12% from last week"
          trendUp={true}
          colorType="blue"
        />
        <StatCard
          title="Passed"
          value={stats.passed}
          icon={CheckCircle2}
          trend={`${stats.totalTests > 0 ? Math.round((stats.passed / stats.totalTests) * 100) : 0}% pass rate`}
          trendUp={true}
          colorType="green"
        />
        <StatCard
          title="Failed"
          value={stats.failed}
          icon={XCircle}
          trend={`${stats.totalTests > 0 ? Math.round((stats.failed / stats.totalTests) * 100) : 0}% fail rate`}
          trendUp={false}
          colorType="red"
        />
        <StatCard
          title="Active Bugs"
          value={stats.openBugs}
          icon={Bug}
          trend="Needs attention"
          colorType="amber"
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
      <RecentBugs tests={testResults} />
    </>
  );
}
