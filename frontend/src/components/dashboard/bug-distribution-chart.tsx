"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart } from "lucide-react";
import { useBugContext } from "@/context/bug-context";
import { SEVERITY_CHART_COLORS, SEVERITY_LABELS } from "@/lib/constants";

export function BugDistributionChart() {
  const { bugs } = useBugContext();

  const distribution = Object.entries(
    bugs.reduce<Record<string, number>>((acc, bug) => {
      acc[bug.severity] = (acc[bug.severity] || 0) + 1;
      return acc;
    }, {})
  ).sort(([a], [b]) => {
    const order = ["critical", "high", "medium", "low"];
    return order.indexOf(a) - order.indexOf(b);
  });

  const total = distribution.reduce((sum, [, count]) => sum + count, 0);

  // Donut chart geometry
  const cx = 50;
  const cy = 50;
  const r = 38;
  const strokeWidth = 14;
  const circumference = 2 * Math.PI * r;

  let cumulativeOffset = 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <PieChart className="h-4 w-4 text-primary" />
          Bug Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          {/* Donut SVG */}
          <div className="relative w-32 h-32 shrink-0">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              {/* Background circle */}
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke="currentColor"
                strokeOpacity="0.06"
                strokeWidth={strokeWidth}
              />
              {/* Segments */}
              {distribution.map(([severity, count]) => {
                const pct = count / total;
                const dashLength = pct * circumference;
                const dashGap = circumference - dashLength;
                const offset = cumulativeOffset;
                cumulativeOffset += dashLength;

                return (
                  <circle
                    key={severity}
                    cx={cx}
                    cy={cy}
                    r={r}
                    fill="none"
                    stroke={SEVERITY_CHART_COLORS[severity]}
                    strokeWidth={strokeWidth}
                    strokeDasharray={`${dashLength} ${dashGap}`}
                    strokeDashoffset={-offset}
                    strokeLinecap="round"
                    className="transition-all duration-700 ease-out"
                    style={{
                      animation: `donut-fill 1s ease-out forwards`,
                    }}
                  />
                );
              })}
            </svg>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold">{total}</span>
              <span className="text-[0.6rem] text-muted-foreground">Total</span>
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-col gap-2.5 flex-1">
            {distribution.map(([severity, count]) => {
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <div key={severity} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: SEVERITY_CHART_COLORS[severity] }}
                    />
                    <span className="text-xs font-medium">
                      {SEVERITY_LABELS[severity]}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold">{count}</span>
                    <span className="text-[0.65rem] text-muted-foreground w-8 text-right">
                      {pct}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
