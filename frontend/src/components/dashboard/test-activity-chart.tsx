"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";

export function TestActivityChart({
  data,
}: {
  data: {
    day: string;
    passed: number;
    failed: number;
  }[];
}) {
  const maxVal = Math.max(...data.map((d) => d.passed + d.failed), 1) * 1.15;
  const chartWidth = 100;
  const chartHeight = 50;
  const barWidth = chartWidth / Math.max(data.length, 1);
  const barGap = Math.min(barWidth * 0.12, 2);
  const actualBarW = Math.min(barWidth - barGap, 10);

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Recent Test Activity
          </CardTitle>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-sm bg-primary" />
              <span className="text-muted-foreground">Passed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-sm bg-red-400" />
              <span className="text-muted-foreground">Failed</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight + 8}`}
          className="w-full h-48"
          preserveAspectRatio="none"
          role="img"
          aria-label="Test activity bar chart showing passed and failed tests"
        >
          {[0.25, 0.5, 0.75, 1].map((ratio) => (
            <line
              key={ratio}
              x1="0"
              y1={chartHeight * (1 - ratio)}
              x2={chartWidth}
              y2={chartHeight * (1 - ratio)}
              stroke="currentColor"
              strokeOpacity="0.06"
              strokeWidth="0.15"
            />
          ))}

          {data.map((d, i) => {
            const passedH = (d.passed / maxVal) * chartHeight;
            const failedH = (d.failed / maxVal) * chartHeight;
            const x = i * barWidth + barGap / 2;

            return (
              <g key={d.day}>
                <rect
                  x={x}
                  width={actualBarW * 0.48}
                  y={chartHeight - passedH}
                  height={passedH}
                  rx="0.5"
                  className="fill-primary"
                  opacity="0.85"
                >
                  <animate attributeName="height" from="0" to={passedH} dur="0.6s" fill="freeze" begin={`${i * 0.04}s`} />
                  <animate attributeName="y" from={chartHeight} to={chartHeight - passedH} dur="0.6s" fill="freeze" begin={`${i * 0.04}s`} />
                </rect>

                <rect
                  x={x + actualBarW * 0.52}
                  width={actualBarW * 0.48}
                  y={chartHeight - failedH}
                  height={failedH}
                  rx="0.5"
                  className="fill-red-400"
                  opacity="0.8"
                >
                  <animate attributeName="height" from="0" to={failedH} dur="0.6s" fill="freeze" begin={`${i * 0.04}s`} />
                  <animate attributeName="y" from={chartHeight} to={chartHeight - failedH} dur="0.6s" fill="freeze" begin={`${i * 0.04}s`} />
                </rect>

                <text
                  x={x + actualBarW / 2}
                  y={chartHeight + 5}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize="2"
                  fontWeight="500"
                >
                  {new Date(d.day).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </text>
              </g>
            );
          })}
        </svg>
      </CardContent>
    </Card>
  );
}
