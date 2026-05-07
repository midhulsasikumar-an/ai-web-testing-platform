"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { TerminalLog } from "@/components/shared/terminal-log";
import { TestConfigForm } from "./test-config-form";
import { TestResultCard } from "./test-result-card";
import { AIFindingsPanel } from "./ai-findings-panel";
import { useTestRunner } from "@/hooks/use-test-runner";

// ── Component ──────────────────────────────────────────────────────

export function TestRunner() {
  const {
    url,
    githubUrl,
    testType,
    loading,
    result,
    streamLines,
    aiFindings,
    streamRef,
    setUrl,
    setGithubUrl,
    setTestType,
    runTest,
  } = useTestRunner();

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Left column: Config + Stream */}
      <div className="lg:col-span-3 space-y-6">
        <TestConfigForm
          url={url}
          onUrlChange={setUrl}
          githubUrl={githubUrl}
          onGithubUrlChange={setGithubUrl}
          testType={testType}
          onTestTypeChange={setTestType}
          loading={loading}
          onRunTest={runTest}
        />

        {/* Live Result Stream */}
        {(streamLines.length > 0 || loading) && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <div
                  className={`h-2 w-2 rounded-full ${loading ? "bg-green-500 animate-pulse" : "bg-muted-foreground"}`}
                />
                Live Result Stream
              </CardTitle>
            </CardHeader>
            <div className="px-6 pb-6">
              <TerminalLog
                entries={streamLines}
                showCursor={loading}
                scrollRef={streamRef}
              />
            </div>
          </Card>
        )}

        {/* Test Result */}
        {result && <TestResultCard result={result} />}
      </div>

      {/* Right column: AI Findings */}
      <div className="lg:col-span-2 space-y-4">
        <AIFindingsPanel findings={aiFindings} />
      </div>
    </div>
  );
}
