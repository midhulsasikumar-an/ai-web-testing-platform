"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { StreamLogLine } from "@/types";
import { useBugContext } from "@/context/bug-context";
import type { TestApiResponse } from "@/services/test-api";
import {
  startTest as callStartTest,
  getTestById,
} from "@/services/test-api";

// ── Stream messages ──────────────────────────

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

const TERMINAL_TEST_STATUSES = new Set([
  "completed",
  "completed_with_failures",
  "failed",
  "cancelled",
  "timed_out",
]);

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ITERATIONS = 600;
const STUCK_THRESHOLD = 20; // 20 polls * 3s = 60s with no status change => stuck

// ── Hook ──────────────────────────────────────

export function useTestRunner() {
  const { addTestResult } = useBugContext();

  const [url, setUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [projectName, setProjectName] = useState("");
  const [testType, setTestType] = useState<"full" | "ai" | "accessibility">("full");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestApiResponse | null>(null);
  const [streamLines, setStreamLines] = useState<StreamLogLine[]>([]);

  const streamLinesRef = useRef<StreamLogLine[]>([]);
  const streamRef = useRef<HTMLDivElement>(null);
  const cancelledRef = useRef(false);
  const runIdRef = useRef<string | null>(null);

  // Auto-scroll stream container
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamLines]);

  useEffect(() => {
    return () => {
      cancelledRef.current = true;
      runIdRef.current = null;
    };
  }, []);

  const appendStream = useCallback((line: StreamLogLine) => {
    setStreamLines((prev) => {
      const next = [...prev, line];
      streamLinesRef.current = next;
      return next;
    });
  }, []);

  const runTest = useCallback(async () => {
    if (!url.trim()) return;

    cancelledRef.current = false;
    setLoading(true);
    setResult(null);
    setStreamLines([]);
    streamLinesRef.current = [];

    try {
      // 1. Initial stream
      for (const line of INITIAL_STREAM) {
        if (cancelledRef.current) return;
        await new Promise((r) => setTimeout(r, 400));
        appendStream(line);
      }

      appendStream({
        time: "00:03",
        level: "info",
        msg: `Dispatching AI probe to ${url}...`,
      });

      // 2. Start backend test
      const startResponse = await callStartTest(
        url,
        projectName || "Untitled Project",
        testType
      );

      runIdRef.current = startResponse.test_id;

      appendStream({
        time: "00:04",
        level: "info",
        msg: `Test started with ID ${startResponse.test_id}`,
      });

      // 3. Poll backend
      let testData: TestApiResponse | undefined;
      let iterations = 0;
      let lastSeenStatus: string | null = null;
      let pollsSinceLastChange = 0;

      while (!cancelledRef.current && iterations < MAX_POLL_ITERATIONS) {
        iterations += 1;
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        if (cancelledRef.current) return;

        try {
          testData = await getTestById(startResponse.test_id);
        } catch (pollError) {
          appendStream({
            time: "00:05",
            level: "warn",
            msg: `Polling error (will retry): ${pollError instanceof Error ? pollError.message : "unknown"}`,
          });
          continue;
        }

        if (testData.status !== lastSeenStatus) {
          lastSeenStatus = testData.status;
          pollsSinceLastChange = 0;
        } else {
          pollsSinceLastChange += 1;
        }

        appendStream({
          time: "00:05",
          level: "info",
          msg: `Current status: ${testData.status}`,
        });

        if (TERMINAL_TEST_STATUSES.has(testData.status)) break;

        // If the status has not changed for a long time, surface a warning
        // so the user knows the backend watchdog is taking over.
        if (pollsSinceLastChange === STUCK_THRESHOLD) {
          appendStream({
            time: "00:05",
            level: "warn",
            msg: "No status change in 60s. The execution watchdog will force a timeout if this persists.",
          });
        }
      }

      if (cancelledRef.current) return;

      if (!testData) {
        throw new Error("Test data not received from backend");
      }

      // 4. Stream results from backend (NO DECISION LOGIC)
      for (const res of testData.results) {
        if (cancelledRef.current) return;
        await new Promise((r) => setTimeout(r, 600));

        appendStream({
          time: "00:06",
          level: res.status === "pass" ? "success" : "error",
          msg: `${res.test}: ${res.status.toUpperCase()} ${
            res.details ? `(${res.details})` : ""
          }`,
        });
      }

      // 5. FINAL RESULT (backend is source of truth)
      if (cancelledRef.current) return;
      setResult(testData);
      addTestResult(testData);
    } catch {
      if (!cancelledRef.current) {
        appendStream({
          time: "00:04",
          level: "error",
          msg: "Failed to connect to AI backend. Falling back to simulation...",
        });

        for (const line of FALLBACK_STREAM) {
          if (cancelledRef.current) return;
          await new Promise((r) => setTimeout(r, 400));
          appendStream(line);
        }
      }
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
      runIdRef.current = null;
    }
  }, [url, projectName, testType, appendStream, addTestResult]);

  return {
    url,
    setUrl,
    githubUrl,
    setGithubUrl,
    projectName,
    setProjectName,
    testType,
    setTestType,
    runTest,
    loading,
    result,
    streamLines,
    streamRef,
  };
}
