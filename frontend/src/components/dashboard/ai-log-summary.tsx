"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TerminalLog } from "@/components/shared/terminal-log";
import { Terminal } from "lucide-react";

const logEntries = [
  { time: "10:32:14", level: "info" as const, msg: "AI scan initiated for https://app.example.com/login" },
  { time: "10:32:16", level: "info" as const, msg: "Detected a printer for set 3 features. All failed tests involve the login module." },
  { time: "10:32:18", level: "warn" as const, msg: "Pattern detected: criticals involving form elements during high-latency spikes." },
  { time: "10:32:20", level: "error" as const, msg: "Anomaly: 3 regression failures in checkout since last deploy (build #1847)" },
  { time: "10:32:22", level: "success" as const, msg: "Recommendation: Roll back payment gateway integration. Run accessibility re-scan." },
  { time: "10:33:01", level: "info" as const, msg: "Scanning dependency tree for known vulnerabilities..." },
  { time: "10:33:04", level: "warn" as const, msg: "2 outdated packages detected with known CVEs: lodash@4.17.15, axios@0.21.0" },
  { time: "10:33:08", level: "success" as const, msg: "Full scan complete. 4 actionable items generated." },
];

export function AILogSummary() {
  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Terminal className="h-4 w-4 text-primary" />
            AI Log Summary
          </CardTitle>
          <span className="text-[0.65rem] text-muted-foreground font-mono">
            Last updated: 2 min ago
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <TerminalLog entries={logEntries} maxHeight="max-h-56" showCursor />
      </CardContent>
    </Card>
  );
}
