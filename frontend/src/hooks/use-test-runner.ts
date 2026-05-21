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

    try {
      // 1. Initial stream
      for (const line of INITIAL_STREAM) {
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

      appendStream({
        time: "00:04",
        level: "info",
        msg: `Test started with ID ${startResponse.test_id}`,
      });

      // 3. Poll backend
      let testData: TestApiResponse ;

      while (true) {
        await new Promise((r) => setTimeout(r, 3000));

        testData = await getTestById(startResponse.test_id);

        appendStream({
          time: "00:05",
          level: "info",
          msg: `Current status: ${testData.status}`,
        });

        if (testData.status !== "running") break;
      }

      // 4. Stream results from backend (NO DECISION LOGIC)
      for (const res of testData.results) {
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
      if (!testData) {
        throw new Error("Test data not received from backend");
      }
      setResult(testData);
      addTestResult(testData);
    } catch {
      appendStream({
        time: "00:04",
        level: "error",
        msg: "Failed to connect to AI backend. Falling back to simulation...",
      });

      for (const line of FALLBACK_STREAM) {
        await new Promise((r) => setTimeout(r, 400));
        appendStream(line);
      }
    } finally {
      setLoading(false);
    }
  }, [url, projectName, testType, appendStream, addTestResult]);

  return {
    url,
    githubUrl,
    projectName,
    testType,
    loading,
    result,
    streamLines,
    streamRef,
    setUrl,
    setGithubUrl,
    setProjectName,
    setTestType,
    runTest,
  };
}