"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { TerminalLog } from "@/components/shared/terminal-log";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { MetadataField } from "@/components/shared/metadata-field";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDateLong, formatTime, formatDuration } from "@/lib/formatters";
import { TEST_TYPE_CONFIG } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
  ArrowLeft, CheckCircle2, XCircle, Globe,
  Clock, Terminal, Bug, ExternalLink, Play,
  Calendar,
} from "lucide-react";

export default function TestDetailPage() {
  const params = useParams();
  const { getTestById, getBugById } = useBugContext();
  const test = getTestById(params.id as string);

  if (!test) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Terminal className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-muted-foreground font-medium">Test not found.</p>
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Link>
      </div>
    );
  }

  const typeConfig = TEST_TYPE_CONFIG[test.testType || "full"];
  const TypeIcon = typeConfig.icon;
  const linkedBug = test.bugId ? getBugById(test.bugId) : null;

  return (
    <>
      <Header title="Test Log Details">
        <Link href="/test-history" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Link>
        <Link href="/run-test" className={cn(buttonVariants({ size: "sm" }))}>
          <Play className="h-4 w-4 mr-2" />
          Re-run
        </Link>
      </Header>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Result banner */}
          <Card className={
            test.status === "passed"
              ? "border-green-500/30 bg-gradient-to-r from-green-50/50 to-transparent"
              : "border-red-500/30 bg-gradient-to-r from-red-50/50 to-transparent"
          }>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl shrink-0 ${
                  test.status === "passed" ? "bg-green-100" : "bg-red-100"
                }`}>
                  {test.status === "passed" ? (
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold">
                      Test {test.status === "passed" ? "Passed" : "Failed"}
                    </h2>
                    <Badge variant={test.status === "passed" ? "secondary" : "destructive"}>
                      {test.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{test.details}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Stream Logs */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-primary" />
                  Execution Log
                </CardTitle>
                <span className="text-[0.65rem] text-muted-foreground font-mono">
                  {test.streamLogs?.length || 0} entries
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {test.streamLogs && test.streamLogs.length > 0 ? (
                <TerminalLog entries={test.streamLogs} maxHeight="max-h-96" />
              ) : (
                <div className="rounded-lg bg-[#0d1117] p-8">
                  <EmptyState icon={Terminal} title="No stream logs available for this test run." />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Linked Bug */}
          {linkedBug && (
            <Card className="border-red-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Bug className="h-4 w-4 text-red-500" />
                  Bug Created from This Test
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Link
                  href={`/bugs/${linkedBug.id}`}
                  className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted/20 hover:bg-muted/40 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-red-500 font-medium">{linkedBug.id}</span>
                      <SeverityBadge severity={linkedBug.severity} />
                    </div>
                    <p className="text-sm font-medium mt-1 group-hover:underline">{linkedBug.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{linkedBug.description}</p>
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0 mt-1" />
                </Link>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebar — Metadata */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Test Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MetadataField icon={Terminal} label="Test ID">
                <p className="text-sm font-mono font-medium">{test.id}</p>
              </MetadataField>

              <MetadataField icon={Globe} label="Target URL">
                <a href={test.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline flex items-center gap-1 break-all">
                  {test.url}
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              </MetadataField>

              <MetadataField icon={TypeIcon} label="Test Type">
                <div className="flex items-center gap-1.5">
                  <TypeIcon className="h-3.5 w-3.5 text-primary" />
                  <span className="text-sm font-medium">{typeConfig.label}</span>
                </div>
              </MetadataField>

              <MetadataField icon={Clock} label="Duration">
                <p className="text-sm font-mono font-medium">{formatDuration(test.duration)}</p>
              </MetadataField>

              <MetadataField icon={Calendar} label="Timestamp">
                <div className="text-sm">
                  <p>{formatDateLong(test.timestamp)}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(test.timestamp)}</p>
                </div>
              </MetadataField>

              <MetadataField icon={test.status === "passed" ? CheckCircle2 : XCircle} label="Result">
                <Badge variant={test.status === "passed" ? "secondary" : "destructive"}>
                  {test.status}
                </Badge>
              </MetadataField>

              {test.bugId && (
                <MetadataField icon={Bug} label="Linked Bug">
                  <Link href={`/bugs/${test.bugId}`} className="text-sm text-red-500 font-mono font-medium hover:underline">
                    {test.bugId}
                  </Link>
                </MetadataField>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
