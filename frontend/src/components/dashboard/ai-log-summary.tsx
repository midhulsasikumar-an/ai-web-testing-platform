"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TerminalLog } from "@/components/shared/terminal-log";
import { Terminal } from "lucide-react";
import { AILog } from "@/services/dashboard-api";

export function AILogSummary({
  aiLogs = [],
}: {
  aiLogs?: AILog[];
}) {

  if (aiLogs.length === 0) {
    return (
      <Card className="col-span-full lg:col-span-2">
        <CardContent className="text-sm text-muted-foreground">
          No AI logs available
        </CardContent>
      </Card>
    );
  }

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
        <TerminalLog
          entries={aiLogs}
          maxHeight="max-h-56"
          showCursor
        />
      </CardContent>
    </Card>
  );
}