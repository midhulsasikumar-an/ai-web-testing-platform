"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  className?: string;
  colorType?: "primary" | "green" | "red" | "amber" | "blue";
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  className,
  colorType = "primary",
}: StatCardProps) {

  const colors = {
    primary: { bg: "bg-primary", text: "text-primary", light: "bg-primary/10" },
    green: { bg: "bg-green-500", text: "text-green-600", light: "bg-green-500/10" },
    red: { bg: "bg-red-500", text: "text-red-500", light: "bg-red-500/10" },
    amber: { bg: "bg-amber-500", text: "text-amber-600", light: "bg-amber-500/10" },
    blue: { bg: "bg-blue-500", text: "text-blue-500", light: "bg-blue-500/10" },
  }[colorType];

  return (
    <Card className={cn("relative overflow-hidden transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group", className)}>
      <div className={cn("absolute top-0 left-0 right-0 h-1 rounded-t-lg", colors.bg)} />

      <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg transition-colors", colors.light)}>
          <Icon className={cn("h-4 w-4", colors.text)} />
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        <div className="text-3xl font-bold tracking-tight">
          {value.toLocaleString()}
        </div>
        {trend && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {trendUp !== undefined && (
              <span className={cn(
                "text-xs font-semibold",
                trendUp ? "text-green-600" : "text-red-500"
              )}>
                {trendUp ? "↑" : "↓"}
              </span>
            )}
            <p className="text-xs text-muted-foreground">{trend}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
