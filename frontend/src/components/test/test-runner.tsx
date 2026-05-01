"use client";

import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBugContext, generateBugFromUrl } from "@/context/bug-context";
import { TestResult, StreamLogLine } from "@/lib/types";
import {
  Loader2, CheckCircle2, XCircle, Play, Zap,
  Globe, GitBranch, ScanLine, Accessibility, RefreshCw,
  Code, AlertTriangle,
} from "lucide-react";

// StreamLogLine imported from types

export function TestRunner() {
  const { addBug, addTestResult, aiFindings } = useBugContext();
  const [url, setUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [streamLines, setStreamLines] = useState<StreamLogLine[]>([]);
  const streamLinesRef = useRef<StreamLogLine[]>([]);
  const [testType, setTestType] = useState<"full" | "ai" | "accessibility">("full");
  const streamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamLines]);

  const streamMessages: StreamLogLine[] = [
    { time: "00:00", level: "info", msg: "Initializing Automated Intelligence Probe..." },
    { time: "00:01", level: "info", msg: "Connecting to target environment..." },
    { time: "00:02", level: "success", msg: "Connection established. Starting scan..." },
    { time: "00:03", level: "info", msg: "Phase 1: DOM structure analysis..." },
    { time: "00:04", level: "info", msg: "Phase 2: JavaScript execution monitoring..." },
    { time: "00:05", level: "warn", msg: "Potential issue detected in form elements..." },
    { time: "00:06", level: "info", msg: "Phase 3: Network request analysis..." },
    { time: "00:07", level: "info", msg: "Phase 4: Accessibility audit running..." },
    { time: "00:08", level: "info", msg: "Phase 5: Performance metrics collection..." },
  ];

  function appendStream(line: StreamLogLine) {
    setStreamLines((prev) => {
      const next = [...prev, line];
      streamLinesRef.current = next;
      return next;
    });
  }

  async function runTest() {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    setStreamLines([]);
    streamLinesRef.current = [];

    // Stream log lines one by one
    for (let i = 0; i < streamMessages.length; i++) {
      await new Promise((r) => setTimeout(r, 300 + Math.random() * 400));
      appendStream(streamMessages[i]);
    }

    const passed = Math.random() > 0.5;
    const duration = Math.floor(2000 + Math.random() * 4000);
    const testId = `TEST-${Date.now().toString(36).toUpperCase()}`;

    let bugId: string | undefined;
    if (!passed) {
      await new Promise((r) => setTimeout(r, 300));
      appendStream({ time: "00:09", level: "error", msg: "Critical issue found! Generating bug report..." });
      const bug = generateBugFromUrl(url);
      addBug(bug);
      bugId = bug.id;
      await new Promise((r) => setTimeout(r, 300));
      appendStream({ time: "00:10", level: "error", msg: `Bug ${bug.id} created: ${bug.title}` });
    } else {
      await new Promise((r) => setTimeout(r, 300));
      appendStream({ time: "00:09", level: "success", msg: "All checks passed. No critical issues detected." });
    }

    await new Promise((r) => setTimeout(r, 200));
    appendStream({ time: "00:10", level: "success", msg: `Scan complete. Duration: ${(duration / 1000).toFixed(1)}s` });

    const testResult: TestResult = {
      id: testId,
      url,
      status: passed ? "passed" : "failed",
      timestamp: new Date().toISOString(),
      duration,
      bugId,
      details: passed
        ? "All checks passed. No issues detected on the target page."
        : `Test failed — a bug (${bugId}) has been automatically created.`,
      testType,
      streamLogs: [...streamLinesRef.current],
    };

    addTestResult(testResult);
    setResult(testResult);
    setLoading(false);
  }

  const testTypes = [
    { id: "full" as const, label: "Full Regression", icon: RefreshCw },
    { id: "ai" as const, label: "AI Scan", icon: ScanLine },
    { id: "accessibility" as const, label: "Accessibility", icon: Accessibility },
  ];

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

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Left column: Config + Stream */}
      <div className="lg:col-span-3 space-y-6">
        {/* Probe header */}
        <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shrink-0">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Automated Intelligence Probe</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Deploy AI agents to crawl, interact, and identify regressions across your environment.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Input fields */}
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5" /> Target URL
              </label>
              <Input
                placeholder="https://app.example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runTest()}
                disabled={loading}
                className="h-11"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <GitBranch className="h-3.5 w-3.5" /> GitHub Repo (optional)
              </label>
              <Input
                placeholder="https://github.com/org/repo"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={loading}
                className="h-11"
              />
            </div>

            {/* Test type toggles */}
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Test Type
              </label>
              <div className="flex flex-wrap gap-2">
                {testTypes.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTestType(id)}
                    disabled={loading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-200 ${
                      testType === id
                        ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20"
                        : "bg-card text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <Button onClick={runTest} disabled={loading || !url.trim()} size="lg" className="w-full mt-2 h-12 text-base font-semibold">
              {loading ? (
                <><Loader2 className="h-5 w-5 animate-spin mr-2" />Scanning...</>
              ) : (
                <><Play className="h-5 w-5 mr-2" />Run Test</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Live Result Stream */}
        {(streamLines.length > 0 || loading) && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${loading ? "bg-green-500 animate-pulse" : "bg-muted-foreground"}`} />
                Live Result Stream
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div ref={streamRef} className="rounded-lg bg-[#0d1117] p-4 max-h-64 overflow-y-auto terminal-log">
                {streamLines.map((line, i) => (
                  <div key={i} className="flex gap-2 py-0.5 leading-relaxed">
                    <span className="log-timestamp shrink-0 select-none">[{line.time}]</span>
                    <span className={`shrink-0 w-3 text-center select-none ${levelColors[line.level]}`}>
                      {levelIcons[line.level]}
                    </span>
                    <span className={levelColors[line.level]}>{line.msg}</span>
                  </div>
                ))}
                {loading && (
                  <div className="flex gap-2 py-0.5 mt-1">
                    <span className="log-timestamp select-none">[--:--]</span>
                    <span className="log-info animate-pulse">▌</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Test Result Card */}
        {result && (
          <Card className={
            result.status === "passed"
              ? "border-green-500/30 bg-green-50/30"
              : "border-red-500/30 bg-red-50/30"
          }>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  {result.status === "passed" ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  Test Result
                </CardTitle>
                <Badge variant={result.status === "passed" ? "secondary" : "destructive"}>
                  {result.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground text-xs">Test ID</span>
                  <p className="font-mono text-xs font-medium">{result.id}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Duration</span>
                  <p className="font-medium">{(result.duration / 1000).toFixed(1)}s</p>
                </div>
                <div className="col-span-2">
                  <span className="text-muted-foreground text-xs">URL</span>
                  <p className="text-xs truncate">{result.url}</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">{result.details}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Right column: AI Findings */}
      <div className="lg:col-span-2 space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Recent AI Findings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {aiFindings.slice(0, 4).map((finding) => (
              <div key={finding.id} className="space-y-2 p-3 rounded-lg border border-border bg-muted/20 hover:bg-muted/40 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-medium leading-tight">{finding.title}</h4>
                  <Badge variant="outline" className={
                    finding.severity === "critical"
                      ? "border-red-500/50 text-red-600 bg-red-50 shrink-0"
                      : finding.severity === "high"
                      ? "border-orange-500/50 text-orange-600 bg-orange-50 shrink-0"
                      : "border-yellow-500/50 text-yellow-700 bg-yellow-50 shrink-0"
                  }>
                    {finding.severity}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {finding.description}
                </p>
                {finding.file && (
                  <div className="flex items-center gap-1.5 text-xs text-primary font-mono">
                    <Code className="h-3 w-3" />
                    {finding.file}
                  </div>
                )}
                {finding.codeSnippet && (
                  <pre className="text-[0.65rem] bg-[#0d1117] text-green-400 p-3 rounded-md overflow-x-auto leading-relaxed">
                    {finding.codeSnippet}
                  </pre>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
