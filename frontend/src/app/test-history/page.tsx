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
import { cn } from "@/lib/utils";
import {
  CheckCircle2, XCircle, Clock, Globe,
  Eye, Play, Terminal, Filter,
} from "lucide-react";
import { useState } from "react";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

type FilterStatus = "all" | "passed" | "failed";

export default function TestHistoryPage() {
  const { testResults } = useBugContext();
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [urlFilter, setUrlFilter] = useState("");

  // Get unique URLs for the URL grouping
  const uniqueUrls = [...new Set(testResults.map((t) => t.url))];

  // Filter results
  const filtered = testResults.filter((t) => {
    if (filter !== "all" && t.status !== filter) return false;
    if (urlFilter && !t.url.toLowerCase().includes(urlFilter.toLowerCase())) return false;
    return true;
  });

  // Group by URL
  const groupedByUrl = uniqueUrls.reduce<Record<string, typeof testResults>>((acc, url) => {
    const tests = filtered.filter((t) => t.url === url);
    if (tests.length > 0) acc[url] = tests;
    return acc;
  }, {});

  const passedCount = testResults.filter((t) => t.status === "passed").length;
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
        <Card>
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
              <Terminal className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{testResults.length}</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Total Runs</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-green-500/20">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{passedCount}</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Passed</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-red-500/20">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <XCircle className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{failedCount}</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Failed</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-3 px-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <Filter className="h-3.5 w-3.5" /> Filters
            </div>
            <div className="flex items-center gap-2">
              {(["all", "passed", "failed"] as FilterStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 capitalize ${
                    filter === s
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
              value={urlFilter}
              onChange={(e) => setUrlFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg text-sm border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 w-full sm:w-64"
            />
          </div>
        </CardContent>
      </Card>

      {/* Grouped results */}
      {Object.keys(groupedByUrl).length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Terminal className="h-8 w-8 mx-auto mb-3 opacity-40" />
            <p className="font-medium">No test runs found</p>
            <p className="text-sm mt-1">Run a test to see results here.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {Object.entries(groupedByUrl).map(([url, tests]) => {
            const urlPassed = tests.filter((t) => t.status === "passed").length;
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
                                variant={test.status === "passed" ? "secondary" : "destructive"}
                                className="text-xs"
                              >
                                <span className="flex items-center gap-1">
                                  {test.status === "passed" ? (
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
