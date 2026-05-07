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
  accentColor?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  accentColor = "bg-primary",
  className,
}: StatCardProps) {
  return (
    <Card className={cn("relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 group", className)}>
      {/* Accent top bar */}
      <div className={cn("absolute top-0 left-0 right-0 h-1 rounded-t-lg", accentColor)} />

      <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn(
          "flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
          accentColor.replace("bg-", "bg-") + "/10"
        )}>
          <Icon className={cn("h-4 w-4", accentColor.replace("bg-", "text-"))} />
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
