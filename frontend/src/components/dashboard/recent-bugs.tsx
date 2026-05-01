"use client";

import Link from "next/link";
import { Bug } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { severityColor, statusColor, formatDate } from "@/components/bugs/bug-utils";
import { Clock } from "lucide-react";

interface RecentBugsProps {
  bugs: Bug[];
}

export function RecentBugs({ bugs }: RecentBugsProps) {
  const recent = bugs.slice(0, 5);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Recent Test Activity
          </CardTitle>
          <Link href="/bugs" className="text-xs text-primary font-medium hover:underline">
            View All →
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead className="w-[80px] text-xs font-semibold">ID</TableHead>
                <TableHead className="text-xs font-semibold">Title</TableHead>
                <TableHead className="w-[90px] text-xs font-semibold">Severity</TableHead>
                <TableHead className="w-[100px] text-xs font-semibold">Status</TableHead>
                <TableHead className="w-[100px] text-xs font-semibold">Assigned</TableHead>
                <TableHead className="w-[100px] text-right text-xs font-semibold">Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    No bugs found. Run a test to get started.
                  </TableCell>
                </TableRow>
              ) : (
                recent.map((bug) => (
                  <TableRow key={bug.id} className="cursor-pointer hover:bg-accent/50 transition-colors">
                    <TableCell className="font-mono text-xs text-primary font-medium">{bug.id}</TableCell>
                    <TableCell>
                      <Link href={`/bugs/${bug.id}`} className="hover:underline font-medium text-sm">
                        {bug.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={severityColor(bug.severity)}>
                        {bug.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={statusColor(bug.status)}>
                        {bug.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {bug.assignedTo && (
                        <div className="flex items-center gap-1.5">
                          <div className="h-5 w-5 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-[0.5rem] font-bold shrink-0">
                            {bug.assignedTo.split(" ").map(n => n[0]).join("")}
                          </div>
                          <span className="text-xs text-muted-foreground truncate max-w-[70px]">
                            {bug.assignedTo.split(" ")[0]}
                          </span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {formatDate(bug.createdAt)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
