"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useBugContext } from "@/context/bug-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ArrowLeft, CheckCircle2, XCircle, Globe,
  Clock, Terminal, RefreshCw, ScanLine,
  Accessibility, Bug, ExternalLink, Play,
  Calendar,
} from "lucide-react";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

const testTypeLabels: Record<string, { label: string; icon: typeof RefreshCw }> = {
  full: { label: "Full Regression", icon: RefreshCw },
  ai: { label: "AI Scan", icon: ScanLine },
  accessibility: { label: "Accessibility", icon: Accessibility },
};

const levelColors: Record<string, string> = {
  info: "log-info",
  warn: "log-warn",
  error: "log-error",
  success: "log-success",
};

const levelIcons: Record<string, string> = {
  info: "ℹ",
  warn: "⚠",
  error: "✕",
  success: "✓",
};

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

  const typeConfig = testTypeLabels[test.testType || "full"];
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
                <div className="rounded-lg bg-[#0d1117] p-4 max-h-96 overflow-y-auto terminal-log">
                  {test.streamLogs.map((line, i) => (
                    <div key={i} className="flex gap-2 py-0.5 leading-relaxed">
                      <span className="log-timestamp shrink-0 select-none">[{line.time}]</span>
                      <span className={`shrink-0 w-3 text-center select-none ${levelColors[line.level]}`}>
                        {levelIcons[line.level]}
                      </span>
                      <span className={levelColors[line.level]}>{line.msg}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg bg-[#0d1117] p-8 text-center">
                  <Terminal className="h-6 w-6 mx-auto mb-2 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground/50">
                    No stream logs available for this test run.
                  </p>
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
                      <Badge variant="outline" className={
                        linkedBug.severity === "critical"
                          ? "border-red-500/50 text-red-600 bg-red-50"
                          : linkedBug.severity === "high"
                          ? "border-orange-500/50 text-orange-600 bg-orange-50"
                          : "border-yellow-500/50 text-yellow-700 bg-yellow-50"
                      }>
                        {linkedBug.severity}
                      </Badge>
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
              {/* Test ID */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <Terminal className="h-3 w-3" /> Test ID
                </div>
                <p className="text-sm font-mono font-medium">{test.id}</p>
              </div>

              {/* URL */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <Globe className="h-3 w-3" /> Target URL
                </div>
                <a
                  href={test.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline flex items-center gap-1 break-all"
                >
                  {test.url}
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              </div>

              {/* Test Type */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <TypeIcon className="h-3 w-3" /> Test Type
                </div>
                <div className="flex items-center gap-1.5">
                  <TypeIcon className="h-3.5 w-3.5 text-primary" />
                  <span className="text-sm font-medium">{typeConfig.label}</span>
                </div>
              </div>

              {/* Duration */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <Clock className="h-3 w-3" /> Duration
                </div>
                <p className="text-sm font-mono font-medium">
                  {(test.duration / 1000).toFixed(1)}s
                </p>
              </div>

              {/* Date/Time */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <Calendar className="h-3 w-3" /> Timestamp
                </div>
                <div className="text-sm">
                  <p>{formatDate(test.timestamp)}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(test.timestamp)}</p>
                </div>
              </div>

              {/* Status */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  {test.status === "passed" ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
                  )}
                  Result
                </div>
                <Badge variant={test.status === "passed" ? "secondary" : "destructive"}>
                  {test.status}
                </Badge>
              </div>

              {/* Bug ID */}
              {test.bugId && (
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                    <Bug className="h-3 w-3" /> Linked Bug
                  </div>
                  <Link
                    href={`/bugs/${test.bugId}`}
                    className="text-sm text-red-500 font-mono font-medium hover:underline"
                  >
                    {test.bugId}
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
