"use client";

import Link from "next/link";
import type { Bug } from "@/types";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { AvatarCircle } from "@/components/shared/avatar-circle";
import { MiniStatCard } from "@/components/shared/mini-stat-card";
import { formatDate } from "@/lib/formatters";
import { Eye, AlertTriangle, CheckCircle2, Flame, Search, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface BugTableProps {
  bugs: Bug[];
}

export function BugTable({ bugs }: BugTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const criticalCount = bugs.filter((b) => b.severity === "critical").length;
  const resolvedCount = bugs.filter((b) => b.status === "resolved" || b.status === "closed").length;
  const fixRate = bugs.length > 0 ? Math.round((resolvedCount / bugs.length) * 100) : 0;
  const activeCount = bugs.filter((b) => b.status === "open" || b.status === "in-progress").length;

  const filteredBugs = bugs.filter((bug) => {
    const matchesSearch = bug.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          bug.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSeverity = severityFilter === "all" || bug.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  });

  return (
    <div className="space-y-4">
      {/* AI Summary Bar */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
        <CardContent className="py-3 px-4">
          <div className="flex items-center gap-2 text-sm">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
              <AlertTriangle className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="font-medium">AI Log Summary:</span>
            <span className="text-muted-foreground">
              Detected a pattern in the last 3 failures. Most failures originate from the login module and checkout flow.
              High correlation with mobile viewports. Recommending accessibility re-scan.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card className="shadow-sm">
        <CardContent className="py-3 px-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-2">
                <Filter className="h-3.5 w-3.5" /> Severity
              </div>
              {(["all", "critical", "high", "medium", "low"]).map((s) => (
                <button
                  key={s}
                  onClick={() => setSeverityFilter(s)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 capitalize ${
                    severityFilter === s
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
                placeholder="Search bugs by title or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9 text-sm rounded-full bg-muted/50 border-transparent focus:border-primary/50 focus:bg-background transition-colors"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bug Table */}
      <Card className="shadow-sm overflow-hidden border-border">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow>
                <TableHead className="w-[80px] text-xs font-semibold">ID</TableHead>
                <TableHead className="min-w-[200px] text-xs font-semibold">Title</TableHead>
                <TableHead className="w-[100px] text-xs font-semibold">Priority</TableHead>
                <TableHead className="w-[120px] text-xs font-semibold">Assigned To</TableHead>
                <TableHead className="w-[100px] text-xs font-semibold">Status</TableHead>
                <TableHead className="w-[100px] text-xs font-semibold">Date</TableHead>
                <TableHead className="w-[60px] text-right text-xs font-semibold">View</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredBugs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    {bugs.length === 0 ? "No bugs recorded yet. Run a test to get started." : "No bugs found matching your filters."}
                  </TableCell>
                </TableRow>
              ) : (
                filteredBugs.map((bug) => (
                  <TableRow key={bug.id} className="hover:bg-accent/30 transition-colors">
                    <TableCell className="font-mono text-xs text-primary font-medium">{bug.id}</TableCell>
                    <TableCell className="font-medium max-w-[300px] md:max-w-md">
                      <Link href={`/bugs/${bug.id}`} className="hover:text-primary transition-colors text-sm truncate block" title={bug.title}>
                        {bug.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <SeverityBadge severity={bug.severity} />
                    </TableCell>
                    <TableCell>
                      {bug.assignedTo ? (
                        <div className="flex items-center gap-1.5">
                          <AvatarCircle name={bug.assignedTo} size="sm" />
                          <span className="text-xs text-muted-foreground truncate max-w-[80px]">
                            {bug.assignedTo}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Unassigned</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={bug.status} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(bug.createdAt)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/bugs/${bug.id}`} className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "h-8 w-8 hover:bg-primary/10 hover:text-primary")}>
                        <Eye className="h-4 w-4" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Summary Stats Footer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <MiniStatCard icon={Flame} value={criticalCount} label="Critical Open" color="red" borderColor="border-red-500/20" />
        <MiniStatCard icon={CheckCircle2} value={`${fixRate}%`} label="Fix Rate" color="green" borderColor="border-green-500/20" />
        <MiniStatCard icon={AlertTriangle} value={activeCount} label="Active" color="amber" borderColor="border-amber-500/20" />
      </div>
    </div>
  );
}
