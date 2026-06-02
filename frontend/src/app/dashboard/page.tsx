"use client";

import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/dashboard/stat-card";
import { AIHealthWidget } from "@/components/dashboard/ai-health-widget";
import { TestSuccessRateChart } from "@/components/dashboard/test-success-rate-chart";
import { LiveTelemetryTerminal } from "@/components/dashboard/live-telemetry-terminal";
import { LiveActivityFeed } from "@/components/dashboard/live-activity-feed";
import { LatestTestRunsTable } from "@/components/dashboard/latest-test-runs-table";
import { useAuth } from "@/context/auth-context";
import {
  Activity,
  AlertTriangle,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { getDashboardStats, DashboardStatsResponse } from "@/services/dashboard-api";

function formatRiskLevel(value: string | undefined | null): string {
  if (!value) return "Unknown";
  const normalized = value.toLowerCase();
  if (normalized === "unknown") return "Unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function riskLevelColor(value: string | undefined | null): string {
  const normalized = (value || "").toLowerCase();
  if (normalized === "high") return "text-red-600";
  if (normalized === "medium") return "text-amber-600";
  if (normalized === "low") return "text-emerald-600";
  return "text-slate-500";
}

function getStabilityGrade(health?: number | null) {
  if (typeof health !== 'number' || Number.isNaN(health) || health <= 0) return "—";
  if (health >= 95) return "A+";
  if (health >= 90) return "A";
  if (health >= 85) return "A-";
  if (health >= 80) return "B+";
  if (health >= 75) return "B";
  if (health >= 70) return "C";
  return "D";
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { isReady } = useAuth();

  useEffect(() => {
    if (!isReady) {
      return;
    }

    let active = true;

    async function loadStats() {
      try {
        setLoading(true);
        setLoadError(null);
        const data = await getDashboardStats();
        if (active) {
          setStats(data);
        }
      } catch (err) {
        if (active) {
          setLoadError(err instanceof Error ? err.message : "Failed to load dashboard stats");
        }
        if (err instanceof Error && err.message.includes("401 Unauthorized")) {
          if (active) setStats(null);
          return;
        }
        console.error("Failed to load dashboard stats", err);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadStats();
    return () => {
      active = false;
    };
  }, [isReady]);

  if (!isReady || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col gap-5">
        <Header title="AI Testing Command Center" description="Real-time health, risk, and activity across your test runs." eyebrow="Overview" />
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-[13px] text-red-700">
          <p className="font-semibold">Dashboard metrics are unavailable.</p>
          <p className="mt-1 break-words">{loadError}</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex flex-col gap-5">
        <Header title="AI Testing Command Center" description="Real-time health, risk, and activity across your test runs." eyebrow="Overview" />
        <div className="rounded-xl border border-border bg-slate-50 p-5 text-[13px] text-slate-500">
          Dashboard metrics are not available right now.
        </div>
      </div>
    );
  }

  const testSuccessRate = stats.total_tests > 0
    ? (stats.passed / stats.total_tests) * 100
    : null;

  const riskLevel = stats.ai_summary?.risk_level ?? null;
  const stabilityGrade = getStabilityGrade(stats.average_health ?? null);

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="AI Testing Command Center"
        description="Real-time health, risk, and activity across your test runs."
        eyebrow="Overview"
      />

      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          <AIHealthWidget score={typeof stats.average_health === "number" && stats.average_health > 0 ? Math.round(stats.average_health) : null} />

          <div className="grid grid-cols-2 gap-3 col-span-1 lg:col-span-2">
            <StatCard
              title="Total Executions"
              value={stats.total_tests ?? "—"}
              icon={Activity}
              trend={stats.total_tests > 0 ? "From recorded runs" : "No runs yet"}
            />
            <StatCard
              title="Active Failures"
              value={stats.open_bugs ?? "—"}
              icon={AlertTriangle}
              trend={stats.open_bugs > 0 ? "Requires attention" : "No active bugs"}
              trendColor={stats.open_bugs > 0 ? "text-red-500" : "text-slate-500"}
              className={stats.open_bugs > 0 ? "text-red-600" : undefined}
            />
            <StatCard
              title="Stability Index"
              value={stabilityGrade}
              icon={Scale}
              trend={stabilityGrade === "—" ? "Awaiting health scores" : `Based on ${stats.average_health}/100`}
            />
            <StatCard
              title="AI Risk Level"
              value={`${formatRiskLevel(riskLevel)} Risk`}
              icon={ShieldCheck}
              trend={stats.ai_summary?.summary || "No summary available"}
              trendColor={riskLevelColor(riskLevel)}
            />
          </div>

          <TestSuccessRateChart
            rate={testSuccessRate}
            data={stats.test_activity}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LiveTelemetryTerminal logs={stats.ai_logs} />
          </div>
          <div className="lg:col-span-1">
            <LiveActivityFeed logs={stats.ai_logs} />
          </div>
        </div>

        <div className="grid grid-cols-1">
          <LatestTestRunsTable tests={stats.recent_tests} />
        </div>
      </div>
    </div>
  );
}
