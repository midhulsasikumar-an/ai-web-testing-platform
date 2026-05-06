"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge } from "@/components/shared/severity-badge";
import type { AIFinding } from "@/types";
import { AlertTriangle, Code } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface AIFindingsPanelProps {
  findings: AIFinding[];
  /** Maximum number of findings to display */
  limit?: number;
}

// ── Component ──────────────────────────────────────────────────────

export function AIFindingsPanel({ findings, limit = 4 }: AIFindingsPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Recent AI Findings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {findings.slice(0, limit).map((finding) => (
          <div
            key={finding.id}
            className="space-y-2 p-3 rounded-lg border border-border bg-muted/20 hover:bg-muted/40 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <h4 className="text-sm font-medium leading-tight">
                {finding.title}
              </h4>
              <SeverityBadge severity={finding.severity} className="shrink-0" />
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {finding.description}
            </p>
            {finding.file && (
              <div className="flex items-center gap-1.5 text-xs text-primary font-mono">
                <Code className="h-3 w-3" />
                {finding.file}
              </div>
            )}
            {finding.codeSnippet && (
              <pre className="text-[0.65rem] bg-[#0d1117] text-green-400 p-3 rounded-md overflow-x-auto leading-relaxed">
                {finding.codeSnippet}
              </pre>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
