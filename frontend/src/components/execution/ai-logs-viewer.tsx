"use client";

import React from "react";
import { useExecutionStore } from "@/store/execution-store";
import { Terminal } from "lucide-react";

export function AILogsViewer() {
  const { logs } = useExecutionStore();

  return (
    <div className="bg-[#0D1117] rounded-lg border border-gray-800 overflow-hidden shadow-xl">
      <div className="flex items-center gap-2 px-4 py-3 bg-[#161B22] border-b border-gray-800">
        <Terminal className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-mono text-gray-300">pulse-engine.log</span>
      </div>
      <div className="p-4 h-[300px] overflow-y-auto font-mono text-sm space-y-2">
        {logs.length === 0 ? (
          <div className="text-gray-500 italic">Waiting for logs...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-gray-600 shrink-0">{log.time}</span>
              <span className={`
                ${log.level === 'error' ? 'text-red-400' : ''}
                ${log.level === 'warn' ? 'text-amber-400' : ''}
                ${log.level === 'success' ? 'text-green-400' : ''}
                ${log.level === 'info' ? 'text-blue-400' : ''}
              `}>
                [{log.level.toUpperCase()}]
              </span>
              <span className="text-gray-300">{log.msg}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
