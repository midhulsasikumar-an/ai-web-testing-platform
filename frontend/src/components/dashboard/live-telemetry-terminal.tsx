"use client";

import { Terminal } from "lucide-react";
import { useRef, useMemo } from "react";
import { AILog } from "@/services/dashboard-api";

interface LiveTelemetryTerminalProps {
  logs?: AILog[];
}

export function LiveTelemetryTerminal({ logs = [] }: LiveTelemetryTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const telemetry = useMemo(() => {
    if (!logs || logs.length === 0) {
      return [
        "[14:20:05] SUCCESS Smoke test: Homepage",
        "[14:22:11] INFO Analyzing checkout latency...",
        "[14:23:45] INFO Patching 'login-module' hotfix",
        "[14:25:30] WARNING 404 detected on /api/v1/auth",
        "[14:26:12] INFO Running AI vulnerability scan..."
      ];
    }
    
    return logs.map(log => 
      `[${log.time.substring(11, 19) || '14:20:05'}] ${log.level === 'error' ? 'WARNING' : log.level.toUpperCase()} ${log.msg}`
    );
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
    <div className="flex flex-col h-full bg-[#1A1A1A] rounded-xl overflow-hidden shadow-lg border border-slate-800">
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#2D2D2D] border-b border-[#3D3D3D]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#FF5F56]"></div>
            <div className="w-3 h-3 rounded-full bg-[#FFBD2E]"></div>
            <div className="w-3 h-3 rounded-full bg-[#27C93F]"></div>
          </div>
          <span className="ml-2 text-xs font-medium text-slate-300 flex items-center gap-2">
            Live System Telemetry
          </span>
        </div>
        <Terminal className="h-4 w-4 text-slate-400" />
      </div>

      {/* Terminal Body */}
      <div 
        ref={containerRef}
        className="p-4 font-mono text-[13px] text-slate-300 h-[280px] overflow-y-auto space-y-1.5"
      >
        {telemetry.map((log, i) => (
          <div key={i} className="flex">
            <span className="opacity-50 mr-3 shrink-0">{log.split("]")[0] + "]"}</span>
            <span>{renderColoredLog(log.split("]").slice(1).join("]"))}</span>
          </div>
        ))}
        {/* Blinking cursor */}
        <div className="animate-pulse w-2 h-4 bg-slate-400 mt-2"></div>
      </div>
    </div>
  );
}
