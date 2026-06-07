"use client";

import { useMemo } from "react";
import { Bot, Sparkles, AlertTriangle, Cpu, CheckCircle2, OctagonAlert, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DashboardStatsResponse } from "@/services/dashboard-api";

interface SystemTelemetryProps {
  stats: DashboardStatsResponse;
}

type EventLevel = "success" | "info" | "warning" | "error";
type InsightTone = "info" | "success" | "warning" | "critical";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatProjectName(project: string): string {
  if (!project) return "Untitled project";
  return project
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusToLevel(status: string | undefined | null): EventLevel {
  const normalized = (status ?? "").toLowerCase();
  if (normalized === "pass" || normalized === "passed" || normalized === "success") return "success";
  if (normalized === "fail" || normalized === "failed" || normalized === "error") return "error";
  if (normalized === "warning" || normalized === "warn" || normalized === "timeout" || normalized === "timed_out") return "warning";
  return "info";
}

function formatTime(date: string | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function formatDateLabel(date: string | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleString("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

type FeedEvent = {
  id: string;
  time: string;
  level: EventLevel;
  category: string;
  message: string;
};

const eventLevelClass: Record<EventLevel, { dot: string; chip: string; chipText: string }> = {
  success: { dot: "bg-emerald-500", chip: "border-emerald-200/60 bg-emerald-500/10", chipText: "text-emerald-300" },
  info: { dot: "bg-blue-500", chip: "border-blue-200/60 bg-blue-500/10", chipText: "text-blue-300" },
  warning: { dot: "bg-amber-500", chip: "border-amber-200/60 bg-amber-500/10", chipText: "text-amber-300" },
  error: { dot: "bg-red-500", chip: "border-red-200/60 bg-red-500/10", chipText: "text-red-300" },
};

function buildEvents(stats: DashboardStatsResponse): FeedEvent[] {
  const events: FeedEvent[] = [];
  const today = todayIso();

  for (const test of stats.recent_tests ?? []) {
    const level = statusToLevel(test.overall_status);
    const project = formatProjectName(test.project);
    const isToday = test.date === today;

    if (level === "success") {
      events.push({
        id: `pass-${test.test_id}`,
        time: test.date,
        level: "success",
        category: "TEST PASSED",
        message: `${project} regression completed successfully${isToday ? "" : ""}`,
      });
    } else if (level === "error") {
      events.push({
        id: `fail-${test.test_id}`,
        time: test.date,
        level: "error",
        category: "TEST FAILED",
        message: `${project} failed validation — review the report`,
      });
    } else if (level === "warning") {
      events.push({
        id: `warn-${test.test_id}`,
        time: test.date,
        level: "warning",
        category: "TEST WARNING",
        message: `${project} completed with warnings`,
      });
    } else {
      events.push({
        id: `info-${test.test_id}`,
        time: test.date,
        level: "info",
        category: "TEST RUN",
        message: `${project} recorded a new run`,
      });
    }
  }

  const insights = stats.ai_summary?.insights ?? [];
  insights.slice(0, 3).forEach((insight, index) => {
    if (typeof insight !== "string" || !insight.trim()) return;
    const level: EventLevel = insight.toLowerCase().includes("fail") ? "warning" : "info";
    events.push({
      id: `ai-${index}-${insight.slice(0, 12)}`,
      time: new Date().toISOString(),
      level,
      category: level === "warning" ? "AI ANALYSIS" : "AI INSIGHT",
      message: insight,
    });
  });

  const distribution = stats.bug_distribution ?? { critical: 0, moderate: 0, minor: 0 };
  if (distribution.critical > 0) {
    events.push({
      id: "bug-critical",
      time: new Date().toISOString(),
      level: "error",
      category: "BUG DETECTED",
      message: `${distribution.critical} critical bug${distribution.critical === 1 ? "" : "s"} need attention`,
    });
  } else if (distribution.moderate > 0) {
    events.push({
      id: "bug-moderate",
      time: new Date().toISOString(),
      level: "warning",
      category: "BUG DETECTED",
      message: `${distribution.moderate} moderate bug${distribution.moderate === 1 ? "" : "s"} open`,
    });
  }

  return events.slice(0, 12);
}

type Insight = { id: string; tone: InsightTone; headline: string; detail: string };

function buildAiSummary(stats: DashboardStatsResponse): Insight[] {
  const items: Insight[] = [];
  const distribution = stats.bug_distribution ?? { critical: 0, moderate: 0, minor: 0 };
  const totalBugs = distribution.critical + distribution.moderate + distribution.minor;
  const successRate = stats.total_tests > 0 ? Math.round((stats.passed / stats.total_tests) * 100) : null;

  if (stats.ai_summary?.insights && stats.ai_summary.insights.length > 0) {
    stats.ai_summary.insights.slice(0, 2).forEach((text, index) => {
      if (typeof text !== "string" || !text.trim()) return;
      const lower = text.toLowerCase();
      const tone: InsightTone =
        lower.includes("critical") || lower.includes("fail") || lower.includes("high risk")
          ? "critical"
          : lower.includes("warning") || lower.includes("degraded") || lower.includes("attention")
            ? "warning"
            : lower.includes("stable") || lower.includes("passing") || lower.includes("healthy")
              ? "success"
              : "info";
      items.push({ id: `ai-${index}`, tone, headline: text, detail: "AI insight" });
    });
  }

  if (totalBugs > 0) {
    const tone: InsightTone = distribution.critical > 0 ? "critical" : distribution.moderate > 0 ? "warning" : "info";
    items.push({
      id: "bug-summary",
      tone,
      headline: `${totalBugs} open bug${totalBugs === 1 ? "" : "s"} across active projects`,
      detail: `${distribution.critical} critical · ${distribution.moderate} moderate · ${distribution.minor} minor`,
    });
  }

  if (successRate !== null) {
    const tone: InsightTone = successRate >= 80 ? "success" : successRate >= 60 ? "warning" : "critical";
    items.push({
      id: "success-rate",
      tone,
      headline: `Platform success rate is ${successRate}%`,
      detail: successRate >= 80 ? "Within healthy range" : successRate >= 60 ? "Below target — investigate failures" : "Critical — address failing workflows",
    });
  }

  if (stats.recent_tests.length > 0) {
    const last = stats.recent_tests[0];
    const level = statusToLevel(last.overall_status);
    const project = formatProjectName(last.project);
    if (level === "error") {
      items.push({
        id: "last-run",
        tone: "warning",
        headline: `${project} most recent run needs attention`,
        detail: `Last executed ${formatDateLabel(last.date)}`,
      });
    } else if (level === "success") {
      items.push({
        id: "last-run",
        tone: "success",
        headline: `${project} is currently stable`,
        detail: `Last executed ${formatDateLabel(last.date)}`,
      });
    }
  }

  if (items.length === 0) {
    items.push({
      id: "empty",
      tone: "info",
      headline: "No AI insights yet",
      detail: "Run a test to populate AI-driven recommendations.",
    });
  }

  return items.slice(0, 6);
}

const insightToneClass: Record<InsightTone, { icon: typeof Sparkles; iconWrap: string; iconText: string; chip: string; chipText: string }> = {
  critical: {
    icon: OctagonAlert,
    iconWrap: "bg-red-100",
    iconText: "text-red-700",
    chip: "border-red-200 bg-red-50 text-red-700",
    chipText: "Critical",
  },
  warning: {
    icon: AlertTriangle,
    iconWrap: "bg-amber-100",
    iconText: "text-amber-700",
    chip: "border-amber-200 bg-amber-50 text-amber-700",
    chipText: "Warning",
  },
  success: {
    icon: CheckCircle2,
    iconWrap: "bg-emerald-100",
    iconText: "text-emerald-700",
    chip: "border-emerald-200 bg-emerald-50 text-emerald-700",
    chipText: "Healthy",
  },
  info: {
    icon: Sparkles,
    iconWrap: "bg-blue-100",
    iconText: "text-blue-700",
    chip: "border-blue-200 bg-blue-50 text-blue-700",
    chipText: "Insight",
  },
};

function LiveActivityFeed({ events }: { events: FeedEvent[] }) {
  return (
    <Card variant="elevated" className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between gap-2 border-b border-border/60">
        <div className="space-y-0.5">
          <CardTitle className="text-[14px]">Live Activity</CardTitle>
          <CardDescription>Recent important events across runs, AI, and bugs.</CardDescription>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10.5px] font-semibold text-slate-600">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          Live
        </span>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <div className="relative overflow-hidden rounded-b-xl bg-slate-950">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
              <span className="ml-2 font-mono text-[11px] text-slate-400">activity_feed</span>
            </div>
            <span className="font-mono text-[10.5px] text-slate-500">last 24h</span>
          </div>
          {events.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Cpu className="mx-auto h-4 w-4 text-slate-500" />
              <p className="mt-2 text-[12px] text-slate-400">No events yet — run a test to populate the feed.</p>
            </div>
          ) : (
            <ul className="max-h-[24rem] space-y-1.5 overflow-y-auto px-4 py-3 font-mono text-[12px]">
              {events.map((event) => {
                const tokens = eventLevelClass[event.level];
                return (
                  <li
                    key={event.id}
                    className="flex items-start gap-2.5 rounded-md border border-slate-800/70 bg-slate-950/70 px-2.5 py-1.5"
                  >
                    <span className="shrink-0 text-slate-500">[{formatTime(event.time)}]</span>
                    <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", tokens.dot)} />
                    <span
                      className={cn(
                        "shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                        tokens.chip,
                        tokens.chipText
                      )}
                    >
                      {event.category}
                    </span>
                    <span className="break-words text-slate-200">{event.message}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function AiSummaryCard({ insights }: { insights: Insight[] }) {
  return (
    <Card variant="elevated" className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between gap-2 border-b border-border/60">
        <div className="space-y-0.5">
          <CardTitle className="text-[14px]">AI Summary</CardTitle>
          <CardDescription>Actionable insights, not duplicate statistics.</CardDescription>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10.5px] font-semibold text-blue-700">
          <Bot className="h-3 w-3" />
          {insights.length} insight{insights.length === 1 ? "" : "s"}
        </span>
      </CardHeader>
      <CardContent className="space-y-2">
        {insights.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/60 p-4 text-center text-[12px] text-slate-500">
            <Sparkles className="mx-auto mb-1.5 h-4 w-4 text-slate-400" />
            Insights will appear after a test run.
          </div>
        ) : (
          <ul className="space-y-2">
            {insights.map((insight) => {
              const tokens = insightToneClass[insight.tone];
              const Icon = tokens.icon;
              return (
                <li
                  key={insight.id}
                  className="flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white p-3 shadow-xs-token"
                >
                  <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-md", tokens.iconWrap)}>
                    <Icon className={cn("h-4 w-4", tokens.iconText)} />
                  </div>
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      <p className="text-[13px] font-semibold leading-snug text-slate-900">
                        {insight.headline}
                      </p>
                    </div>
                    <p className="text-[11.5px] leading-relaxed text-slate-500">{insight.detail}</p>
                  </div>
                  <span
                    className={cn(
                      "inline-flex shrink-0 items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                      tokens.chip,
                      tokens.chipText
                    )}
                  >
                    {tokens.chipText}
                    <ChevronRight className="h-2.5 w-2.5" />
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function SystemTelemetry({ stats }: SystemTelemetryProps) {
  const events = useMemo(() => buildEvents(stats), [stats]);
  const insights = useMemo(() => buildAiSummary(stats), [stats]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <LiveActivityFeed events={events} />
      <AiSummaryCard insights={insights} />
    </div>
  );
}

export { LiveActivityFeed, AiSummaryCard };
