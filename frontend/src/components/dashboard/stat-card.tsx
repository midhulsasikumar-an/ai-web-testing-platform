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
    <div className={cn("bg-[#F8FAFC] rounded-2xl p-6 flex flex-col justify-between shadow-sm border border-slate-100", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-slate-700">{title}</h3>
        <Icon className="h-4 w-4 text-slate-400" />
      </div>
      
      <div className="mt-4">
        <div className="text-3xl font-bold tracking-tight text-slate-900">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        
        {trend && (
          <div className={cn("flex flex-col mt-2", trendColor)}>
            {TrendIcon && (
              <div className="flex items-center mb-1">
                <TrendIcon className="h-4 w-4" />
              </div>
            )}
            <span className="text-[12px]">{trend}</span>
          </div>
        )}
      </div>
    </div>
  );
}
