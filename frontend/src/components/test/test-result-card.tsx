"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TestResult } from "@/types";
import { CheckCircle2, XCircle } from "lucide-react";
import { formatDuration } from "@/lib/formatters";

// ── Types ──────────────────────────────────────────────────────────

interface TestResultCardProps {
  result: TestResult;
}

// ── Component ──────────────────────────────────────────────────────

export function TestResultCard({ result }: TestResultCardProps) {
  const isPassed = result.status === "passed";

  return (
    <Card
      className={
        isPassed
          ? "border-green-500/30 bg-green-50/30"
          : "border-red-500/30 bg-red-50/30"
      }
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {isPassed ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <XCircle className="h-5 w-5 text-red-600" />
            )}
            Test Result
          </CardTitle>
          <Badge variant={isPassed ? "secondary" : "destructive"}>
            {result.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground text-xs">Test ID</span>
            <p className="font-mono text-xs font-medium">{result.id}</p>
          </div>
          <div>
            <span className="text-muted-foreground text-xs">Duration</span>
            <p className="font-medium">{formatDuration(result.duration)}</p>
          </div>
          <div className="col-span-2">
            <span className="text-muted-foreground text-xs">URL</span>
            <p className="text-xs truncate">{result.url}</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{result.details}</p>
      </CardContent>
    </Card>
  );
}
