"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/formatters";
import { Clock } from "lucide-react";
import { RecentTest } from "@/services/dashboard-api";

interface RecentBugsProps {
  tests: RecentTest[];
}

export function RecentBugs({ tests }: RecentBugsProps) {
  const recent = tests.slice(0, 5);

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
                <TableHead className="text-xs font-semibold">
                  Project
                </TableHead>

                <TableHead className="text-xs font-semibold">
                  URL
                </TableHead>

                <TableHead className="w-[100px] text-xs font-semibold">
                  Status
                </TableHead>

                <TableHead className="w-[100px] text-xs font-semibold">
                  Health
                </TableHead>

                <TableHead className="w-[120px] text-xs font-semibold">
                  Test Type
                </TableHead>

                <TableHead className="w-[140px] text-right text-xs font-semibold">
                  Date
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    No tests found. Run a test to get started.
                  </TableCell>
                </TableRow>
              ) : (
                recent.map((test) => (
                  <TableRow
                    key={test.test_id}
                    className="cursor-pointer hover:bg-accent/50 transition-colors"
                  >
                    <TableCell className="font-medium">
                      {test.project}
                    </TableCell>

                    <TableCell className="max-w-[250px] truncate text-xs text-muted-foreground">
                      {test.url}
                    </TableCell>

                    <TableCell>
                      <span
                        className={`text-xs font-semibold px-2 py-1 rounded-md ${
                          test.overall_status === "pass"
                            ? "bg-green-100 text-green-700"
                            : test.overall_status === "warning"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {test.overall_status}
                      </span>
                    </TableCell>

                    <TableCell>
                      <span className="text-sm font-medium">
                        {test.health_score ?? 0}/100
                      </span>
                    </TableCell>

                    <TableCell className="capitalize">
                      {test.test_type ?? "full"}
                    </TableCell>

                    <TableCell className="text-right text-xs text-muted-foreground">
                      {formatDate(test.date ?? "")}
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
