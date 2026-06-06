"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import { buttonVariants } from "@/components/ui/button";
import { MiniStatCard } from "@/components/shared/mini-stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { useFilteredList } from "@/hooks/use-filtered-list";
import { formatDate, formatTime } from "@/lib/formatters";
import { extractHostname, resolveTestDisplayName, truncateText, canonicalizeUrl } from "@/lib/test-display";
import { cn } from "@/lib/utils";
import {
  CheckCircle2, XCircle, Globe, Eye,
  Play, Terminal, Filter,
} from "lucide-react";

type FilterStatus = "all" | "pass" | "fail" | "warning";

const FILTER_LABELS: Record<FilterStatus, string> = {
  all: "All",
  pass: "Passed",
  fail: "Failed",
  warning: "Warning",
};

const NON_PASSING_STATUSES = new Set([
  "fail",
  "timeout",
  "cancelled",
  "error",
  "warning",
]);

function isFailingStatus(value: string | undefined | null): boolean {
  return NON_PASSING_STATUSES.has(String(value || "").toLowerCase());
}

function formatDuration(test: { updated_at?: string; created_at?: string; runtime_ms?: number }): string {
  if (typeof test.runtime_ms === "number" && Number.isFinite(test.runtime_ms) && test.runtime_ms >= 0) {
    const seconds = test.runtime_ms / 1000;
    if (seconds < 1) {
      return `${Math.max(1, Math.round(test.runtime_ms))}ms`;
    }
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return `${minutes}m ${remainder}s`;
  }
  const start = test.created_at ? new Date(test.created_at).getTime() : NaN;
  const end = test.updated_at ? new Date(test.updated_at).getTime() : NaN;
  if (Number.isFinite(start) && Number.isFinite(end) && end >= start) {
    const seconds = (end - start) / 1000;
    if (seconds < 1) return `${Math.max(1, Math.round(end - start))}ms`;
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return `${minutes}m ${remainder}s`;
  }
  return "—";
}

export default function TestHistoryPage() {
  const { testResults } = useBugContext();

  const {
    filtered,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  } = useFilteredList(testResults, {
    getStatus: (t) => t.overall_status || "unknown",
    getSearchText: (t) => {
      const testName = resolveTestDisplayName(t);
      const website = extractHostname(t.target_url || t.url);
      return `${testName} ${website}`;
    },
  });

  const uniqueUrls = [...new Set(testResults.map((t) => canonicalizeUrl(t.target_url || t.url)).filter(Boolean))];

  // Group filtered results by canonical URL so trailing slashes, mixed case,
  // and tracking parameters don't fragment the same target across groups.
  const groupedByUrl = uniqueUrls.reduce<Record<string, typeof testResults>>((acc, url) => {
    const tests = filtered.filter((t) => canonicalizeUrl(t.target_url || t.url) === url);
    if (tests.length > 0) acc[url] = tests;
    return acc;
  }, {});

  const passedCount = testResults.filter((t) => String(t.overall_status || "").toLowerCase() === "pass").length;
  const failedCount = testResults.filter((t) => isFailingStatus(t.overall_status)).length;

  return (
    <>
      <Header
        title="Test History"
        description="Browse and revisit logs from all previously tested websites."
        eyebrow="Results"
      >
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          New Test
        </Link>
      </Header>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <MiniStatCard icon={Terminal} value={testResults.length} label="Total Runs" color="blue" />
        <MiniStatCard icon={CheckCircle2} value={passedCount} label="Passed" color="green" borderColor="border-emerald-200" />
        <MiniStatCard icon={XCircle} value={failedCount} label="Failed" color="red" borderColor="border-red-200" />
      </div>

      <Card>
        <CardContent className="py-3 px-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex items-center gap-1.5 text-eyebrow">
              <Filter className="h-3.5 w-3.5" /> Filters
            </div>
            <div className="flex items-center gap-2">
              {(["all", "pass", "fail", "warning"] as FilterStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
                    statusFilter === s
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-card text-muted-foreground border-border hover:bg-accent"
                  }`}
                >
                  {FILTER_LABELS[s]}
                </button>
              ))}
            </div>
            <div className="flex-1" />
            <input
              type="text"
              placeholder="Search by test name or website..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-3 py-1.5 rounded-lg text-sm border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 w-full sm:w-64"
            />
          </div>
        </CardContent>
      </Card>

      {/* Grouped results */}
      {Object.keys(groupedByUrl).length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState icon={Terminal} title="No test runs found" description="Run a test to see results here." />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {Object.entries(groupedByUrl).map(([url, tests]) => {
            const urlPassed = tests.filter((t) => String(t.overall_status || "").toLowerCase() === "pass").length;
            const urlFailed = tests.filter((t) => isFailingStatus(t.overall_status)).length;

            return (
              <Card key={url}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Globe className="h-4 w-4 text-primary" />
                      <span className="truncate max-w-lg">{url}</span>
                    </CardTitle>
                    <div className="flex items-center gap-3 text-xs shrink-0">
                      <span className="flex items-center gap-1 text-green-600 font-medium">
                        <CheckCircle2 className="h-3.5 w-3.5" /> {urlPassed}
                      </span>
                      <span className="flex items-center gap-1 text-red-500 font-medium">
                        <XCircle className="h-3.5 w-3.5" /> {urlFailed}
                      </span>
                      <span className="text-muted-foreground">
                        {tests.length} run{tests.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border border-border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/30">
                          <TableHead className="w-[210px] text-xs font-semibold">Test Name</TableHead>
                          <TableHead className="w-[90px] text-xs font-semibold">Status</TableHead>
                          <TableHead className="w-[90px] text-xs font-semibold">Type</TableHead>
                          <TableHead className="text-xs font-semibold">Details</TableHead>
                          <TableHead className="w-[80px] text-xs font-semibold">Duration</TableHead>
                          <TableHead className="w-[100px] text-xs font-semibold">Date</TableHead>
                          <TableHead className="w-[50px] text-xs font-semibold text-right">Logs</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {tests.map((test) => (
                          <TableRow key={test.test_id} className="hover:bg-accent/50 transition-colors">
                            <TableCell className="text-xs text-primary font-medium">
                              {truncateText(resolveTestDisplayName(test), 80)}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  String(test.overall_status || "").toLowerCase() === "pass"
                                    ? "secondary"
                                    : "destructive"
                                }
                                className="text-xs"
                              >
                                <span className="flex items-center gap-1">
                                  {String(test.overall_status || "").toLowerCase() === "pass" ? (
                                    <CheckCircle2 className="h-3 w-3" />
                                  ) : (
                                    <XCircle className="h-3 w-3" />
                                  )}

                                  {test.overall_status || "unknown"}
                                </span>
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <span className="text-xs text-muted-foreground capitalize">
                                {test.run_type || test.test_type || "full"}
                              </span>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground max-w-[250px] truncate">
                              {test.ai_summary || "No summary available"}
                            </TableCell>
                            <TableCell className="text-xs font-mono">
                              {formatDuration(test)}
                            </TableCell>
                            <TableCell>
                              <div className="text-xs text-muted-foreground">
                                <div>{formatDate(test.created_at || "")}</div>
                                <div className="text-[0.6rem]">{formatTime(test.created_at || "")}</div>
                              </div>
                            </TableCell>
                            <TableCell className="text-right">
                              <Link
                                href={`/test-history/${test.test_id}`}
                                className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "h-7 w-7")}
                                title="View full test logs"
                              >
                                <Eye className="h-3.5 w-3.5" />
                              </Link>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
