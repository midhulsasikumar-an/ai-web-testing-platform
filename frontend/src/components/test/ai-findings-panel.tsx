"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import type { TestApiResponse } from "@/services/test-api";

// ── Types ──────────────────────────────────────────────────────────

interface AIFindingsPanelProps {
  result: TestApiResponse | null;
}

// ── Component ──────────────────────────────────────────────────────

export function AIFindingsPanel({ result }: AIFindingsPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Recent AI Findings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!result ? (
          <p className="text-sm text-muted-foreground">
            Run a test to see AI-powered insights.
          </p>
        ) : (
          <>
            {/* AI Summary */}
            <div>
              <h3 className="text-sm font-semibold mb-1">AI Summary</h3>
              <p className="text-sm text-muted-foreground">
                {result.ai_summary}
              </p>
            </div>

            {/* Critical Issues */}
            {result.insights?.critical?.length ? (
              <div>
                <h3 className="text-sm font-semibold text-red-500 mb-2">
                  Critical Issues
                </h3>

                <ul className="space-y-2">
                  {result.insights.critical.map((issue, index) => (
                    <li
                      key={index}
                      className="text-sm border rounded-md p-2 bg-red-50/30"
                    >
                      {issue}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Moderate Issues */}
            {result.insights?.moderate?.length ? (
              <div>
                <h3 className="text-sm font-semibold text-yellow-500 mb-2">
                  Moderate Issues
                </h3>

                <ul className="space-y-2">
                  {result.insights.moderate.map((issue, index) => (
                    <li
                      key={index}
                      className="text-sm border rounded-md p-2 bg-yellow-50/30"
                    >
                      {issue}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Minor Issues */}
            {result.insights?.minor?.length ? (
              <div>
                <h3 className="text-sm font-semibold text-blue-500 mb-2">
                  Minor Issues
                </h3>

                <ul className="space-y-2">
                  {result.insights.minor.map((issue, index) => (
                    <li
                      key={index}
                      className="text-sm border rounded-md p-2 bg-blue-50/30"
                    >
                      {issue}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Recommendations */}
            {result.recommendations?.length ? (
              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Recommendations
                </h3>

                <ul className="space-y-2">
                  {result.recommendations.map((rec, index) => (
                    <li
                      key={index}
                      className="text-sm border rounded-md p-2"
                    >
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
