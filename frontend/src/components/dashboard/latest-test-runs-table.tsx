"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, ArrowRight, Monitor, Smartphone, Globe, Shield, Terminal } from "lucide-react";
import Link from "next/link";
import { RecentTest } from "@/services/dashboard-api";
import { resolveTestDisplayName, truncateText } from "@/lib/test-display";

interface LatestTestRunsTableProps {
  tests: RecentTest[];
}

const getIconForProject = (project: string) => {
  if (project.includes("mobile") || project.includes("m.")) return <Smartphone className="h-4 w-4 text-slate-500" />;
  if (project.includes("api")) return <Monitor className="h-4 w-4 text-slate-500" />;
  if (project.includes("auth") || project.includes("portal")) return <Globe className="h-4 w-4 text-slate-500" />;
  if (project.includes("staging")) return <Shield className="h-4 w-4 text-slate-500" />;
  return <Globe className="h-4 w-4 text-slate-500" />;
};

const getStatusBadge = (status: string | null | undefined) => {
  const s = (status ?? "warning").toLowerCase();
  if (s === "pass" || s === "passed" || s === "completed" || s === "success") {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Completed</span>
      </div>
    );
  }
  if (s === "failed" || s === "error") {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 border border-red-200">
        <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
        <span className="text-[10px] font-bold text-red-700 uppercase tracking-wider">Failed</span>
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200">
      <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
      <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Warning</span>
    </div>
  );
};

export function LatestTestRunsTable({ tests }: LatestTestRunsTableProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border bg-white">
        <div className="flex items-center justify-between">
          <CardTitle>Latest Test Runs</CardTitle>
          <Link href="/test-history" className="text-[13px] font-medium text-primary flex items-center gap-1 hover:underline">
            View All History
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </CardHeader>

      <CardContent>
        {tests.length === 0 ? (
          <div className="py-8 text-center">
            <Terminal className="mx-auto h-6 w-6 text-slate-400" />
            <p className="mt-3 text-sm font-medium text-slate-900">No recent test runs</p>
            <p className="mt-1 text-muted-sm">Run a test to populate this dashboard with live data.</p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-5 py-3 text-eyebrow">Test Name</th>
                  <th className="px-3 py-3 text-eyebrow">Test Type</th>
                  <th className="px-3 py-3 text-eyebrow">Status</th>
                  <th className="px-3 py-3 text-eyebrow text-center">Bugs</th>
                  <th className="px-3 py-3 text-eyebrow">Stability</th>
                  <th className="px-3 py-3 text-eyebrow">Last Run</th>
                  <th className="px-5 py-3 text-eyebrow text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tests.map((test, index) => {
                  const healthScore = typeof test.health_score === "number" ? test.health_score : 0;
                  const bugCount = (test as RecentTest & { bugs?: number }).bugs ?? 0;
                  const displayName = resolveTestDisplayName(test);
                  return (
                    <tr key={test.test_id || index} className="border-b border-border/60 last:border-b-0 hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 border border-border">
                            {getIconForProject(test.project || test.url)}
                          </div>
                          <div className="min-w-0">
                            <p className="text-[13px] font-medium text-slate-900 truncate max-w-[260px]">{truncateText(displayName, 60)}</p>
                            {test.url ? (
                              <p className="text-[11px] text-slate-500 truncate max-w-[260px]">{test.url}</p>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3.5 whitespace-nowrap">
                        <span className="text-[13px] text-slate-600">{test.test_type}</span>
                      </td>
                      <td className="px-3 py-3.5 whitespace-nowrap">
                        {getStatusBadge(test.overall_status)}
                      </td>
                      <td className="px-3 py-3.5 whitespace-nowrap text-center">
                        <span className={`text-[13px] font-bold ${bugCount > 0 ? "text-red-500" : "text-slate-600"}`}>
                          {bugCount}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${healthScore > 90 ? "bg-primary" : healthScore > 70 ? "bg-amber-500" : "bg-red-500"}`}
                              style={{ width: `${Math.max(0, Math.min(100, healthScore))}%` }}
                            />
                          </div>
                          <span className={`text-[12px] font-bold ${healthScore > 90 ? "text-primary" : healthScore > 70 ? "text-amber-500" : "text-red-500"}`}>
                            {healthScore}%
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-3.5 whitespace-nowrap">
                        <span className="text-[13px] text-slate-600">{test.date}</span>
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap text-center">
                        <Link
                          href={`/test-history/${test.test_id}`}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                          title="View test run details"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
