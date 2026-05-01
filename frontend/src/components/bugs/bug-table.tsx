"use client";

import Link from "next/link";
import { Bug } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { severityColor, statusColor, formatDate } from "./bug-utils";
import { Eye, AlertTriangle, CheckCircle2, Flame } from "lucide-react";
import { cn } from "@/lib/utils";

interface BugTableProps {
  bugs: Bug[];
}

export function BugTable({ bugs }: BugTableProps) {
  const criticalCount = bugs.filter((b) => b.severity === "critical").length;
  const resolvedCount = bugs.filter((b) => b.status === "resolved" || b.status === "closed").length;
  const fixRate = bugs.length > 0 ? Math.round((resolvedCount / bugs.length) * 100) : 0;
  const activeCount = bugs.filter((b) => b.status === "open" || b.status === "in-progress").length;

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

      {/* Bug Table */}
      <div className="rounded-lg border border-border overflow-hidden bg-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-[80px] text-xs font-semibold">ID</TableHead>
              <TableHead className="text-xs font-semibold">Title</TableHead>
              <TableHead className="w-[90px] text-xs font-semibold">Priority</TableHead>
              <TableHead className="w-[110px] text-xs font-semibold">Assigned To</TableHead>
              <TableHead className="w-[100px] text-xs font-semibold">Status</TableHead>
              <TableHead className="w-[100px] text-xs font-semibold">Date</TableHead>
              <TableHead className="w-[60px] text-right text-xs font-semibold">View</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {bugs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                  No bugs recorded yet. Run a test to get started.
                </TableCell>
              </TableRow>
            ) : (
              bugs.map((bug) => (
                <TableRow key={bug.id} className="hover:bg-accent/50 transition-colors">
                  <TableCell className="font-mono text-xs text-primary font-medium">{bug.id}</TableCell>
                  <TableCell className="font-medium max-w-[300px]">
                    <Link href={`/bugs/${bug.id}`} className="hover:underline text-sm">
                      {bug.title}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={severityColor(bug.severity)}>
                      {bug.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {bug.assignedTo ? (
                      <div className="flex items-center gap-1.5">
                        <div className="h-6 w-6 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-[0.55rem] font-bold shrink-0">
                          {bug.assignedTo.split(" ").map(n => n[0]).join("")}
                        </div>
                        <span className="text-xs text-muted-foreground truncate max-w-[80px]">
                          {bug.assignedTo}
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={statusColor(bug.status)}>
                      {bug.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(bug.createdAt)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Link href={`/bugs/${bug.id}`} className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "h-7 w-7")}>
                      <Eye className="h-3.5 w-3.5" />
                    </Link>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Summary Stats Footer */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-red-500/20">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <Flame className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Critical Open</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-green-500/20">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{fixRate}%</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Fix Rate</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-amber-500/20">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-600">{activeCount}</p>
              <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">Active</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
