"use client";

import { Bot, CheckCircle2, Circle, Clock3, FileText, Loader2, RefreshCw, Sparkles, Bug as BugIcon, Target, BookOpen, Image as ImageIcon, Save, Copy, Edit3 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UIIntent } from "@/components/ai-workspace/chat-primitives";

function getIntentMeta(intent: UIIntent) {
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

const toneRing: Record<"violet" | "blue" | "red" | "emerald" | "slate", string> = {
  violet: "from-violet-500 to-fuchsia-600",
  blue: "from-blue-500 to-indigo-600",
  red: "from-rose-500 to-pink-600",
  emerald: "from-emerald-500 to-teal-600",
  slate: "from-slate-500 to-slate-700",
};

const toneChip: Record<"violet" | "blue" | "red" | "emerald" | "slate", string> = {
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  blue: "border-blue-200 bg-blue-50 text-primary",
  red: "border-red-200 bg-red-50 text-red-700",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
  slate: "border-slate-200 bg-slate-50 text-slate-600",
};

export function IntentChip({ intent, className }: { intent: UIIntent; className?: string }) {
  const meta = getIntentMeta(intent);
  const Icon = meta.icon;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em]", toneChip[meta.tone], className)}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

export function AvatarBot({ tone = "blue", size = "md" }: { tone?: "violet" | "blue" | "red" | "emerald" | "slate"; size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "sm" ? "h-7 w-7" : size === "lg" ? "h-9 w-9" : "h-8 w-8";
  const iconSize = size === "sm" ? "h-3.5 w-3.5" : size === "lg" ? "h-4.5 w-4.5" : "h-4 w-4";
  return (
    <div className={cn("flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-xs-token", sizeClass, toneRing[tone])}>
      <Sparkles className={iconSize} />
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

export function EmptyAssistantHint({ children }: { children?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[12.5px] text-slate-500">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
      <span>{children ?? "Analyzing context and preparing answer…"}</span>
    </div>
  );
}

export function ThinkingDots() {
  return (
    <div className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60" style={{ animationDelay: "0ms" }} />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60" style={{ animationDelay: "120ms" }} />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60" style={{ animationDelay: "240ms" }} />
    </div>
  );
}

export function MessageRoleDivider({ label }: { label: string }) {
  return (
    <div className="mx-auto my-2 flex w-full max-w-3xl items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-slate-400">
      <span className="h-px flex-1 bg-slate-200/60" />
      {label}
      <span className="h-px flex-1 bg-slate-200/60" />
    </div>
  );
}

export function MessageActions({
  onCopy,
  onRegenerate,
  onEdit,
}: {
  onCopy?: () => void;
  onRegenerate?: () => void;
  onEdit?: () => void;
}) {
  const actions: { icon: React.ElementType; label: string; onClick?: () => void; key: string }[] = [
    { icon: Copy, label: "Copy", onClick: onCopy, key: "copy" },
    { icon: RefreshCw, label: "Regenerate", onClick: onRegenerate, key: "regen" },
    { icon: Edit3, label: "Edit", onClick: onEdit, key: "edit" },
  ];
  return (
    <div className={cn("flex items-center gap-0.5 rounded-lg border border-slate-200 bg-white p-0.5 opacity-0 shadow-xs-token transition-opacity group-hover:opacity-100")}>
      {actions.map((a) => {
        if (!a.onClick) return null;
        const Icon = a.icon;
        return (
          <button
            key={a.key}
            onClick={a.onClick}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
            aria-label={a.label}
            title={a.label}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        );
      })}
    </div>
  );
}

export function StructuredToolResult({
  icon,
  label,
  count,
  preview,
  className,
}: {
  icon: React.ElementType;
  label: string;
  count: number;
  preview?: string;
  className?: string;
}) {
  const Icon = icon;
  return (
    <div className={cn("rounded-lg border border-slate-200 bg-slate-50/80 p-2.5", className)}>
      <div className="flex items-center gap-2 text-[11.5px]">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-white text-slate-500">
          <Icon className="h-3 w-3" />
        </div>
        <span className="font-semibold text-slate-700">{label}</span>
        <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-500">
          {count} record{count === 1 ? "" : "s"}
        </span>
      </div>
      {preview ? <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-slate-600">{preview}</p> : null}
    </div>
  );
}
