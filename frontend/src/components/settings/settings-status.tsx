"use client";

import { ReactNode } from "react";
import { CheckCircle2, AlertCircle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type Status = "idle" | "loading" | "success" | "error";

interface SettingsStatusProps {
  status: Status;
  successLabel?: string;
  errorMessage?: string | null;
  loadingLabel?: string;
  className?: string;
  children?: ReactNode;
}

export function SettingsStatus({
  status,
  successLabel = "Saved successfully",
  errorMessage,
  loadingLabel = "Saving…",
  className,
  children,
}: SettingsStatusProps) {
  if (status === "idle" && !children) return null;

  if (status === "loading") {
    return (
      <div className={cn("flex items-center gap-1.5 text-[12px] text-slate-600", className)}>
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>{loadingLabel}</span>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className={cn("flex items-center gap-1.5 text-[12px] font-medium text-emerald-700", className)}>
        <CheckCircle2 className="h-3.5 w-3.5" />
        <span>{successLabel}</span>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className={cn("flex items-center gap-1.5 text-[12px] font-medium text-red-600", className)}>
        <XCircle className="h-3.5 w-3.5" />
        <span className="line-clamp-1">{errorMessage ?? "Something went wrong"}</span>
      </div>
    );
  }

  if (children) {
    return <div className={cn("text-[12px] text-slate-500", className)}>{children}</div>;
  }

  return null;
}

export function StatusPill({ status }: { status: "ok" | "warning" | "error" | "muted" }) {
  if (status === "ok") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10.5px] font-semibold text-emerald-700">
        <CheckCircle2 className="h-3 w-3" /> Healthy
      </span>
    );
  }
  if (status === "warning") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10.5px] font-semibold text-amber-700">
        <AlertCircle className="h-3 w-3" /> Action needed
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10.5px] font-semibold text-red-700">
        <AlertCircle className="h-3 w-3" /> Issue
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10.5px] font-semibold text-slate-500">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" /> Idle
    </span>
  );
}
