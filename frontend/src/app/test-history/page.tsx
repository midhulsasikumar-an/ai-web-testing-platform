"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  Play, Terminal, Filter, Search
} from "lucide-react";
import { Input } from "@/components/ui/input";

type FilterStatus = "all" | "passed" | "failed" | "warning";

export default function TestHistoryPage() {
  const { testResults } = useBugContext();

  const {
    filtered,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  } = useFilteredList(testResults, {
    getStatus: (t) => t.overall_status || "warning",
    getSearchText: (t) => t.url,
  });

  const passedCount = testResults.filter((t) => t.overall_status === "pass").length;
  const failedCount = testResults.filter((t) => t.overall_status === "fail").length;

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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MiniStatCard icon={Terminal} value={testResults.length} label="Total Runs" color="blue" />
        <MiniStatCard icon={CheckCircle2} value={passedCount} label="Passed" color="green" borderColor="border-green-500/20" />
        <MiniStatCard icon={XCircle} value={failedCount} label="Failed" color="red" borderColor="border-red-500/20" />
      </div>

      {/* Filters */}
      <Card className="shadow-sm">
        <CardContent className="py-3 px-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-2">
                <Filter className="h-3.5 w-3.5" /> Filters
              </div>
              {(["all", "passed", "failed", "warning"] as FilterStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 capitalize ${
                    statusFilter === s
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="relative w-full md:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Filter by URL..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9 text-sm rounded-full bg-muted/50 border-transparent focus:border-primary/50 focus:bg-background transition-colors"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Unified Table */}
      {filtered.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState icon={Terminal} title="No test runs found" description="Run a test to see results here." />
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-muted/30">
                <TableRow>
                  <TableHead className="w-[100px] text-xs font-semibold">Test ID</TableHead>
                  <TableHead className="w-[90px] text-xs font-semibold">Status</TableHead>
                  <TableHead className="min-w-[200px] text-xs font-semibold">Target</TableHead>
                  <TableHead className="w-[100px] text-xs font-semibold">Type</TableHead>
                  <TableHead className="w-[120px] text-xs font-semibold">Date</TableHead>
                  <TableHead className="w-[60px] text-xs font-semibold text-right">View</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((test) => (
                  <TableRow key={test.test_id} className="hover:bg-accent/30 transition-colors">
                    <TableCell className="font-mono text-xs text-primary font-medium">{test.test_id}</TableCell>
                    <TableCell>
                      <Badge
                        variant={test.overall_status === "pass" ? "secondary" : "destructive"}
                        className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
                      >
                        {test.overall_status || "warning"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Globe className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="text-sm font-medium truncate max-w-[200px] md:max-w-xs" title={test.url}>
                          {test.url}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-md capitalize">
                        {test.test_type || "full"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">{formatDate(test.created_at || "")}</span>
                        <span className="ml-2 text-[10px] opacity-70">{formatTime(test.created_at || "")}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/test-history/${test.test_id}`}
                        className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "h-8 w-8 hover:bg-primary/10 hover:text-primary")}
                        title="View full test logs"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
    </>
  );
}
