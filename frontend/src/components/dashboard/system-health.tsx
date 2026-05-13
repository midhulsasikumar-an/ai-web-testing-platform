"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield } from "lucide-react";


export function SystemHealth({
  averageHealth,
}: {
  averageHealth: number;
}) {
  const r = 52;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * r;
  const fillLength = (averageHealth / 100) * circumference;
  const gapLength = circumference - fillLength;

  const getColor = (s: number) => {
    if (s >= 80) return { stroke: "#22c55e", bg: "rgba(34,197,94,0.1)", label: "Healthy" };
    if (s >= 60) return { stroke: "#eab308", bg: "rgba(234,179,8,0.1)", label: "Warning" };
    return { stroke: "#ef4444", bg: "rgba(239,68,68,0.1)", label: "Critical" };
  };

  const color = getColor(averageHealth);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        <div className="relative w-36 h-36">
          <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
            {/* Track */}
            <circle
              cx="60"
              cy="60"
              r={r}
              fill="none"
              stroke="currentColor"
              strokeOpacity="0.06"
              strokeWidth={strokeWidth}
            />
            {/* Fill */}
            <circle
              cx="60"
              cy="60"
              r={r}
              fill="none"
              stroke={color.stroke}
              strokeWidth={strokeWidth}
              strokeDasharray={`${fillLength} ${gapLength}`}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
              style={{
                filter: `drop-shadow(0 0 6px ${color.stroke}40)`,
              }}
            />
          </svg>
          {/* Center */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold" style={{ color: color.stroke }}>
              {averageHealth}%
            </span>
            <span className="text-[0.65rem] text-muted-foreground font-medium">
              {color.label}
            </span>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-3 w-full mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-lg font-bold text-green-600">98%</p>
            <p className="text-[0.6rem] text-muted-foreground">Uptime</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-blue-600">245ms</p>
            <p className="text-[0.6rem] text-muted-foreground">Avg Response</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-amber-600">3</p>
            <p className="text-[0.6rem] text-muted-foreground">Alerts</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
