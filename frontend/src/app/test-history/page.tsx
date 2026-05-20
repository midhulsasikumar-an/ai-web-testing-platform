"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
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
import { cn } from "@/lib/utils";
import {
  CheckCircle2, XCircle, Globe, Eye,
  Play, Terminal, Filter,
} from "lucide-react";
import { useTestHistoryStore } from "@/store/test-history-store";
import { useEffect } from "react";

type FilterStatus = "all" | "completed" | "failed";

export default function TestHistoryPage() {
  const { testResults, fetchHistory } = useTestHistoryStore();

  useEffect(() => {
    if (testResults.length === 0) fetchHistory();
  }, [testResults.length, fetchHistory]);

  const {
    filtered,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  } = useFilteredList(testResults, {
    getStatus: (t) => t.status,
    getSearchText: (t) => t.url,
  });

  const uniqueUrls = [...new Set(testResults.map((t) => t.url))];

  // Group filtered results by URL
  const groupedByUrl = uniqueUrls.reduce<Record<string, typeof testResults>>((acc, url) => {
    const tests = filtered.filter((t) => t.url === url);
    if (tests.length > 0) acc[url] = tests;
    return acc;
  }, {});

  const completedCount = testResults.filter((t) => t.status === "completed").length;
  const failedCount = testResults.filter((t) => t.status === "failed").length;

  return (
    <>
      <Header
        title="Test History"
        description="Browse and revisit logs from all previously tested websites."
      >
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          New Test
        </Link>
      </Header>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <MiniStatCard icon={Terminal} value={testResults.length} label="Total Runs" color="blue" />
        <MiniStatCard icon={CheckCircle2} value={completedCount} label="completed" color="green" borderColor="border-green-500/20" />
        <MiniStatCard icon={XCircle} value={failedCount} label="Failed" color="red" borderColor="border-red-500/20" />
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-3 px-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <Filter className="h-3.5 w-3.5" /> Filters
            </div>
            <div className="flex items-center gap-2">
              {(["all", "completed", "failed"] as FilterStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 capitalize ${
                    statusFilter === s
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-card text-muted-foreground border-border hover:bg-accent"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="flex-1" />
            <input
              type="text"
              placeholder="Filter by URL..."
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
            const urlPassed = tests.filter((t) => t.status === "completed").length;
            const urlFailed = tests.filter((t) => t.status === "failed").length;

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
                          <TableHead className="w-[100px] text-xs font-semibold">Test ID</TableHead>
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
                          <TableRow key={test.id} className="hover:bg-accent/50 transition-colors">
                            <TableCell className="font-mono text-xs text-primary font-medium">{test.id}</TableCell>
                            <TableCell>
                              <Badge
                                variant={test.status === "completed" ? "secondary" : "destructive"}
                                className="text-xs"
                              >
                                <span className="flex items-center gap-1">
                                  {test.status === "completed" ? (
                                    <CheckCircle2 className="h-3 w-3" />
                                  ) : (
                                    <XCircle className="h-3 w-3" />
                                  )}
                                  {test.status}
                                </span>
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <span className="text-xs text-muted-foreground capitalize">
                                {test.testType || "full"}
                              </span>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground max-w-[250px] truncate">
                              {test.details}
                            </TableCell>
                            <TableCell className="text-xs font-mono">
                              {(test.duration / 1000).toFixed(1)}s
                            </TableCell>
                            <TableCell>
                              <div className="text-xs text-muted-foreground">
                                <div>{formatDate(test.timestamp)}</div>
                                <div className="text-[0.6rem]">{formatTime(test.timestamp)}</div>
                              </div>
                            </TableCell>
                            <TableCell className="text-right">
                              <Link
                                href={`/test-history/${test.id}`}
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
