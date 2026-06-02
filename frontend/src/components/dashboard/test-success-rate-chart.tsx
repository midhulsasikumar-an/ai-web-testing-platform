"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2 } from "lucide-react";

interface TestSuccessRateChartProps {
  rate: number | null;
  data: { day?: string; passed?: number; failed?: number }[] | null;
}

export function TestSuccessRateChart({ rate, data }: TestSuccessRateChartProps) {
  const hasData = Array.isArray(data) && data.length > 0;

  return (
    <Card className="col-span-1 sm:col-span-2 lg:col-span-2 xl:col-span-1">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            Test Success Rate
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent>
        <div className="flex items-end justify-between h-24 gap-3">
          <div className="text-3xl font-bold tracking-tight text-slate-900 pb-1 shrink-0">
            {typeof rate === "number" && Number.isFinite(rate) ? `${rate.toFixed(1)}%` : "—"}
          </div>

          <div className="flex items-end gap-1.5 h-full pt-2 min-w-0">
            {hasData ? (
              data!.map((d, i) => {
                const total = (d.passed || 0) + (d.failed || 0);
                const maxTotal = Math.max(...data!.map((x) => (x.passed || 0) + (x.failed || 0)), 1);
                const heightPercentage = Math.max(0, Math.min(100, (total / maxTotal) * 100));
                return (
                  <div
                    key={i}
                    className="w-4 md:w-5 bg-primary rounded-t-sm transition-all hover:opacity-80"
                    style={{ height: `${heightPercentage}%` }}
                    title={`${d.passed ?? 0} passed, ${d.failed ?? 0} failed`}
                  />
                );
              })
            ) : (
              <div className="text-muted-sm">No recent activity</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
