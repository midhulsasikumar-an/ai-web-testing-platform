"use client";

import { Bot, CheckCircle2, ChevronRight, Circle, Clock3, FileText, Loader2, RefreshCw, Sparkles, Bug as BugIcon, Target, BookOpen, ImageIcon, Save } from "lucide-react";
import { cn } from "@/lib/utils";

export type UIIntent =
  | "general_chat"
  | "report_analysis"
  | "query_bugs"
  | "screenshot_analysis"
  | "instruction_generation"
  | "memory"
  | "memory_update"
  | "test_run_analysis"
  | "compare_runs"
  | string;

export type UIMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  intent: UIIntent;
  retrievedData: unknown[];
  assistantPayload?: Record<string, unknown>;
};

export function getIntentMeta(intent: UIIntent) {
  switch (intent) {
    case "instruction_generation":
      return { label: "Test Instructions", icon: Sparkles, tone: "violet" as const };
    case "report_analysis":
      return { label: "Report Analysis", icon: FileText, tone: "blue" as const };
    case "query_bugs":
      return { label: "Bug Analysis", icon: BugIcon, tone: "red" as const };
    case "screenshot_analysis":
      return { label: "Screenshot Analysis", icon: ImageIcon, tone: "emerald" as const };
    case "memory_update":
      return { label: "Memory Saved", icon: Save, tone: "emerald" as const };
    case "test_run_analysis":
      return { label: "Test Run Analysis", icon: Target, tone: "blue" as const };
    case "memory":
      return { label: "Memory Recall", icon: BookOpen, tone: "violet" as const };
    case "compare_runs":
      return { label: "Compare Runs", icon: RefreshCw, tone: "blue" as const };
    default:
      return { label: "Assistant", icon: Bot, tone: "slate" as const };
  }
}

const toneMap: Record<"violet" | "blue" | "red" | "emerald" | "slate", { ring: string; bg: string; text: string; chip: string }> = {
  violet:  { ring: "ring-violet-100", bg: "bg-violet-50",  text: "text-violet-700",  chip: "border-violet-200 bg-violet-50 text-violet-700" },
  blue:    { ring: "ring-blue-100",   bg: "bg-blue-50",    text: "text-primary",     chip: "border-blue-200 bg-blue-50 text-primary" },
  red:     { ring: "ring-red-100",    bg: "bg-red-50",     text: "text-red-700",     chip: "border-red-200 bg-red-50 text-red-700" },
  emerald: { ring: "ring-emerald-100",bg: "bg-emerald-50", text: "text-emerald-700", chip: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  slate:   { ring: "ring-slate-200",  bg: "bg-slate-100",  text: "text-slate-700",   chip: "border-slate-200 bg-slate-50 text-slate-600" },
};

export function IntentChip({ intent }: { intent: UIIntent }) {
  const meta = getIntentMeta(intent);
  const Icon = meta.icon;
  const tone = toneMap[meta.tone];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10.5px] font-medium", tone.chip)}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

export function AvatarBot({ tone = "blue", size = "md" }: { tone?: "blue" | "violet" | "red" | "emerald"; size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "sm" ? "h-6 w-6" : size === "lg" ? "h-8 w-8" : "h-7 w-7";
  const iconSize = size === "sm" ? "h-3 w-3" : size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5";
  const gradient = {
    blue: "from-blue-500 to-indigo-600",
    violet: "from-violet-500 to-fuchsia-600",
    red: "from-rose-500 to-pink-600",
    emerald: "from-emerald-500 to-teal-600",
  }[tone];
  return (
    <div className={cn("flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-xs-token", sizeClass, gradient)}>
      <Sparkles className={iconSize} />
    </div>
  );
}

export function StatusDot({ status }: { status: "pending" | "running" | "completed" | "failed" | "warning" | "timeout" | "cancelled" }) {
  if (status === "running") {
    return (
      <span className="relative inline-flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
      </span>
    );
  }
  if (status === "completed") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />;
  }
  if (status === "failed") {
    return <Circle className="h-3.5 w-3.5 text-red-500 fill-red-500" />;
  }
  if (status === "warning" || status === "timeout") {
    return <Circle className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />;
  }
  if (status === "cancelled") {
    return <Circle className="h-3.5 w-3.5 text-slate-400 fill-slate-400" />;
  }
  return <Circle className="h-3.5 w-3.5 text-slate-300" />;
}

export function InlineSpinner({ size = "sm" }: { size?: "xs" | "sm" | "md" }) {
  const dim = size === "xs" ? "h-3 w-3" : size === "md" ? "h-5 w-5" : "h-4 w-4";
  return <Loader2 className={cn("animate-spin text-primary", dim)} />;
}

export function EmptyAssistantHint({ children }: { children?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-slate-500">
      <InlineSpinner size="sm" />
      <span>{children ?? "Analyzing context and preparing answer…"}</span>
    </div>
  );
}

export function MetaTimestamp({ value }: { value?: string }) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return (
    <span className="inline-flex items-center gap-1 text-[10.5px] text-slate-400">
      <Clock3 className="h-3 w-3" />
      {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
    </span>
  );
}

export function MessageGroupDivider() {
  return <div className="mx-auto h-px w-full max-w-3xl bg-slate-200/60" />;
}

export function ChevronDivider({ children }: { children?: React.ReactNode }) {
  return (
    <div className="my-2 flex items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-slate-400">
      <span className="h-px flex-1 bg-slate-200/60" />
      {children}
      <ChevronRight className="h-3 w-3" />
      <span className="h-px flex-1 bg-slate-200/60" />
    </div>
  );
}
