"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";

// Mock chart data — 14 days of test activity
const chartData = [
  { day: "Apr 15", passed: 82, failed: 12 },
  { day: "Apr 16", passed: 95, failed: 8 },
  { day: "Apr 17", passed: 78, failed: 15 },
  { day: "Apr 18", passed: 110, failed: 10 },
  { day: "Apr 19", passed: 88, failed: 18 },
  { day: "Apr 20", passed: 92, failed: 6 },
  { day: "Apr 21", passed: 105, failed: 14 },
  { day: "Apr 22", passed: 98, failed: 11 },
  { day: "Apr 23", passed: 115, failed: 9 },
  { day: "Apr 24", passed: 90, failed: 16 },
  { day: "Apr 25", passed: 102, failed: 13 },
  { day: "Apr 26", passed: 88, failed: 7 },
  { day: "Apr 27", passed: 108, failed: 12 },
  { day: "Apr 28", passed: 96, failed: 10 },
];

export function TestActivityChart() {
  const maxVal = Math.max(...chartData.map((d) => d.passed + d.failed)) * 1.15;
  const chartWidth = 100;
  const chartHeight = 50;
  const barWidth = chartWidth / chartData.length;
  const barGap = barWidth * 0.25;
  const actualBarW = barWidth - barGap;

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
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
          aria-label="Test activity bar chart showing passed and failed tests over the last 14 days"
        >
          {/* Grid lines */}
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

          {/* Bars */}
          {chartData.map((d, i) => {
            const passedH = (d.passed / maxVal) * chartHeight;
            const failedH = (d.failed / maxVal) * chartHeight;
            const x = i * barWidth + barGap / 2;

            return (
              <g key={d.day}>
                {/* Passed bar */}
                <rect
                  x={x}
                  y={chartHeight - passedH - failedH}
                  width={actualBarW * 0.48}
                  height={passedH}
                  rx="0.5"
                  className="fill-primary"
                  opacity="0.85"
                >
                  <animate
                    attributeName="height"
                    from="0"
                    to={passedH}
                    dur="0.6s"
                    fill="freeze"
                    begin={`${i * 0.04}s`}
                  />
                  <animate
                    attributeName="y"
                    from={chartHeight}
                    to={chartHeight - passedH - failedH}
                    dur="0.6s"
                    fill="freeze"
                    begin={`${i * 0.04}s`}
                  />
                </rect>

                {/* Failed bar */}
                <rect
                  x={x + actualBarW * 0.52}
                  y={chartHeight - failedH}
                  width={actualBarW * 0.48}
                  height={failedH}
                  rx="0.5"
                  className="fill-red-400"
                  opacity="0.8"
                >
                  <animate
                    attributeName="height"
                    from="0"
                    to={failedH}
                    dur="0.6s"
                    fill="freeze"
                    begin={`${i * 0.04}s`}
                  />
                  <animate
                    attributeName="y"
                    from={chartHeight}
                    to={chartHeight - failedH}
                    dur="0.6s"
                    fill="freeze"
                    begin={`${i * 0.04}s`}
                  />
                </rect>

                {/* Day label */}
                <text
                  x={x + actualBarW / 2}
                  y={chartHeight + 5}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize="2"
                  fontWeight="500"
                >
                  {d.day.split(" ")[1]}
                </text>
              </g>
            );
          })}
        </svg>
      </CardContent>
    </Card>
  );
}
