"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { TestResult, StreamLogLine } from "@/types";
import { useBugContext } from "@/context/bug-context";
import { generateBugFromUrl } from "@/lib/bug-generators";
import { startTest as callStartTest } from "@/services/test-api";

// ── Stream messages for initial animation ──────────────────────────

const INITIAL_STREAM: StreamLogLine[] = [
  { time: "00:00", level: "info", msg: "Initializing Automated Intelligence Probe..." },
  { time: "00:01", level: "info", msg: "Connecting to target environment..." },
  { time: "00:02", level: "success", msg: "Connection established. Starting scan..." },
];

const FALLBACK_STREAM: StreamLogLine[] = [
  { time: "00:03", level: "info", msg: "Phase 1: DOM structure analysis..." },
  { time: "00:04", level: "info", msg: "Phase 2: JavaScript execution monitoring..." },
  { time: "00:05", level: "warn", msg: "Potential issue detected in form elements..." },
  { time: "00:06", level: "info", msg: "Phase 3: Network request analysis..." },
  { time: "00:07", level: "info", msg: "Phase 4: Accessibility audit running..." },
  { time: "00:08", level: "info", msg: "Phase 5: Performance metrics collection..." },
];

// ── Hook ───────────────────────────────────────────────────────────

export function useTestRunner() {
  const { addBug, addTestResult, aiFindings } = useBugContext();

  const [url, setUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [testType, setTestType] = useState<"full" | "ai" | "accessibility">("full");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [streamLines, setStreamLines] = useState<StreamLogLine[]>([]);
  const streamLinesRef = useRef<StreamLogLine[]>([]);
  const streamRef = useRef<HTMLDivElement>(null);

  // Auto-scroll stream container
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamLines]);

  const appendStream = useCallback((line: StreamLogLine) => {
    setStreamLines((prev) => {
      const next = [...prev, line];
      streamLinesRef.current = next;
      return next;
    });
  }, []);

  const runTest = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    setStreamLines([]);
    streamLinesRef.current = [];

    // 1. Initial streaming animation
    for (const line of INITIAL_STREAM) {
      await new Promise((r) => setTimeout(r, 400));
      appendStream(line);
    }

    try {
      // 2. Call backend
      appendStream({ time: "00:03", level: "info", msg: `Dispatching AI probe to ${url}...` });

      const testData = await callStartTest(url, "Demo Project");

      // 3. Stream backend results
      for (const res of testData.results) {
        await new Promise((r) => setTimeout(r, 600));
        const level = res.status === "pass" ? "success" : "error";
        appendStream({
          time: "00:05",
          level,
          msg: `${res.test}: ${res.status.toUpperCase()} ${res.details ? `(${res.details})` : ""}`,
        });
      }

      const passed = testData.results.every((r) => r.status === "pass");
      const duration = 2000;
      const testId = testData.test_id.substring(0, 8).toUpperCase();

      let bugId: string | undefined;
      if (!passed) {
        appendStream({ time: "00:08", level: "error", msg: "Issues detected. Generating bug report..." });
        const bug = generateBugFromUrl(url);
        addBug(bug);
        bugId = bug.id;
        appendStream({ time: "00:09", level: "error", msg: `Bug ${bug.id} created: ${bug.title}` });
      } else {
        appendStream({ time: "00:08", level: "success", msg: "All backend checks passed." });
      }

      const testResult: TestResult = {
        id: testId,
        url,
        status: passed ? "passed" : "failed",
        timestamp: new Date().toISOString(),
        duration,
        bugId,
        details: passed
          ? "The live AI probe verified the site is accessible and correctly configured."
          : `Test failed — the AI probe identified issues and created bug ${bugId}.`,
        testType,
        streamLogs: [...streamLinesRef.current],
      };

      addTestResult(testResult);
      setResult(testResult);
    } catch {
      appendStream({ time: "00:04", level: "error", msg: "Failed to connect to AI backend. Falling back to simulation..." });
      // Fallback simulation
      for (const line of FALLBACK_STREAM) {
        await new Promise((r) => setTimeout(r, 400));
        appendStream(line);
      }
    } finally {
      setLoading(false);
    }
  }, [url, testType, appendStream, addBug, addTestResult]);

  return {
    // State
    url,
    githubUrl,
    testType,
    loading,
    result,
    streamLines,
    aiFindings,
    streamRef,
    // Actions
    setUrl,
    setGithubUrl,
    setTestType,
    runTest,
  };
}
