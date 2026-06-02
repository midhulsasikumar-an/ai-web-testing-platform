"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Terminal } from "lucide-react";
import { useMemo } from "react";
import { AILog } from "@/services/dashboard-api";

interface LiveTelemetryTerminalProps {
  logs?: AILog[];
}

export function LiveTelemetryTerminal({ logs = [] }: LiveTelemetryTerminalProps) {
  const telemetry = useMemo(() => {
    if (!logs || logs.length === 0) return [];
    return logs.map((log) => `[${(log.time || "").substring(11, 19) || ""}] ${log.level === "error" ? "WARNING" : (log.level || "").toUpperCase()} ${log.msg || ""}`);
  }, [logs]);

  const renderColoredLog = (log: string) => {
    if (log.includes("SUCCESS")) {
      return <><span className="text-emerald-400">SUCCESS</span> {log.split("SUCCESS")[1]}</>;
    }
    if (log.includes("INFO")) {
      return <><span className="text-slate-300">INFO</span> {log.split("INFO")[1]}</>;
    }
    if (log.includes("WARNING")) {
      return <><span className="text-red-400">WARNING</span> {log.split("WARNING")[1]}</>;
    }
    return log;
  };

  return (
    <Card variant="elevated" className="flex flex-col h-full overflow-hidden border-slate-800 bg-[#1A1A1A] shadow-lg-token">
      <CardHeader className="flex flex-row items-center justify-between gap-2 border-b border-slate-800 bg-[#2D2D2D] px-4 py-2.5 group-data-[variant=elevated]/card:pt-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#FF5F56]" />
            <div className="w-3 h-3 rounded-full bg-[#FFBD2E]" />
            <div className="w-3 h-3 rounded-full bg-[#27C93F]" />
          </div>
          <span className="ml-1 text-xs font-medium text-slate-300 truncate">Live System Telemetry</span>
        </div>
        <Terminal className="h-4 w-4 text-slate-400 shrink-0" />
      </CardHeader>

      <CardContent className="font-mono text-[13px] text-slate-300 h-[280px] overflow-y-auto space-y-1.5 bg-[#1A1A1A]">
        {telemetry.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-700 p-4 text-sm text-slate-400">No telemetry available.</div>
        ) : (
          telemetry.map((log, i) => (
            <div key={i} className="flex">
              <span className="opacity-50 mr-3 shrink-0">{log.split("]")[0] + "]"}</span>
              <span>{renderColoredLog(log.split("]").slice(1).join("]"))}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
