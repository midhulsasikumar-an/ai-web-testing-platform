"use client";

import React, { useEffect } from "react";
import { useExecutionStore } from "@/store/execution-store";
import { executionService } from "@/services/execution.service";
import { Loader2, CheckCircle2, PlayCircle, Settings, Search, AlertTriangle } from "lucide-react";
import { WorkflowState } from "@/types";

interface ExecutionMonitorProps {
  executionId: string;
}

const stateIcons: Record<WorkflowState, React.ReactNode> = {
  queued: <PlayCircle className="w-5 h-5 text-gray-400" />,
  running: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
  generating_steps: <Settings className="w-5 h-5 text-purple-500 animate-spin" />,
  executing: <PlayCircle className="w-5 h-5 text-amber-500 animate-pulse" />,
  analyzing: <Search className="w-5 h-5 text-cyan-500 animate-spin" />,
  completed: <CheckCircle2 className="w-5 h-5 text-green-500" />,
  failed: <AlertTriangle className="w-5 h-5 text-red-500" />,
};

const stateLabels: Record<WorkflowState, string> = {
  queued: "Queued",
  running: "Initializing Run",
  generating_steps: "AI Generating Steps",
  executing: "Executing Actions",
  analyzing: "Analyzing Results",
  completed: "Run Completed",
  failed: "Run Failed",
};

export function ExecutionMonitor({ executionId }: ExecutionMonitorProps) {
  const { status, updateStatus, url } = useExecutionStore();

  useEffect(() => {
    // Start polling the backend for execution status
    const interval = setInterval(async () => {
      try {
        const data = await executionService.getExecutionStatus(executionId);
        updateStatus(data.status);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Failed to fetch execution status", error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [executionId, updateStatus]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Live Execution Monitoring</h2>
          <p className="text-sm text-gray-500 mt-1">
            Tracking execution {executionId.slice(0, 8)}... for {url || "target"}
          </p>
        </div>
        
        {status && (
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-full border border-gray-100">
            {stateIcons[status]}
            <span className="font-semibold text-gray-700">{stateLabels[status]}</span>
          </div>
        )}
      </div>

      {/* Pipeline Visualization Placeholder */}
      <div className="relative pt-4 pb-8">
        <div className="absolute top-1/2 left-0 w-full h-1 bg-gray-100 -translate-y-1/2 z-0 rounded"></div>
        <div className="relative z-10 flex justify-between">
          {["queued", "generating_steps", "executing", "analyzing", "completed"].map((step, idx) => {
            const isCurrent = status === step;
            const isPast = status === "completed" || status === "failed" || 
                           (["generating_steps", "executing", "analyzing", "completed"].includes(status || "") && idx < 2); // simplistic check for now
            return (
              <div key={step} className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${
                  isCurrent ? "bg-blue-50 border-blue-500 text-blue-600" :
                  isPast ? "bg-green-500 border-green-500 text-white" : "bg-white border-gray-200 text-gray-400"
                }`}>
                  {idx + 1}
                </div>
                <span className={`text-xs mt-2 font-medium ${isCurrent ? "text-blue-600" : isPast ? "text-green-600" : "text-gray-400"}`}>
                  {stateLabels[step as WorkflowState]?.split(" ")[0]}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
