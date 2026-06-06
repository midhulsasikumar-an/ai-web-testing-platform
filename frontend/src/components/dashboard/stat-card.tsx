"use client";

import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendIcon?: LucideIcon;
  trendColor?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendIcon: TrendIcon,
  trendColor = "text-slate-500",
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "shell-surface rounded-xl border border-border p-5 shadow-xs-token flex flex-col justify-between gap-3",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-eyebrow">{title}</h3>
        <Icon className="h-4 w-4 text-slate-400" />
      </div>

      <div className="space-y-1.5">
        <div className="text-h1 tracking-tight text-slate-900">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>

        {trend && (
          <div className={cn("flex items-start gap-1.5", trendColor)}>
            {TrendIcon && <TrendIcon className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
            <span className="text-[12px] leading-snug">{trend}</span>
          </div>
        )}
      </div>
    </div>
  );
}
