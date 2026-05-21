"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useMemo } from "react";
import type { Bug, DashboardStats, AIFinding } from "@/types";
import {sampleAIFindings } from "@/lib/data";
import { getAllTests } from "@/services/test-api";
import type { TestApiResponse } from "@/services/test-api";
import { generateBugsFromTests } from "@/lib/bug-generators";
import { useAuth } from "@/context/auth-context";

// ── Context shape ──────────────────────────────────────────────────

interface BugContextType {
  bugs: Bug[];
  testResults: TestApiResponse[];
  aiFindings: AIFinding[];
  stats: DashboardStats;
  addBug: (bug: Bug) => void;
  updateBugStatus: (id: string, status: Bug["status"]) => void;
  addTestResult: (result: TestApiResponse) => void;
  getBugById: (id: string) => Bug | undefined;
  getTestById: (id: string) => TestApiResponse | undefined;
}

const BugContext = createContext<BugContextType | undefined>(undefined);

// ── Provider ───────────────────────────────────────────────────────

export function BugProvider({ children }: { children: React.ReactNode }) {
  const { isReady, token } = useAuth();
  const [manualBugs, setManualBugs] = useState<Bug[]>([]);
  const [testResults, setTestResults] = useState<TestApiResponse[]>([]);
  const [aiFindings] = useState<AIFinding[]>(sampleAIFindings);
  useEffect(() => {
    if (!isReady || !token) {
      return;
    }

    let active = true;

    async function loadTests() {
      try {
        const tests = await getAllTests(token ?? undefined);

        if (active) {
          setTestResults(tests);
        }
      } catch (error) {
        console.error("Failed to load tests:", error);
      }
    }

    loadTests();

    return () => {
      active = false;
    };
  }, [isReady, token]);

  const visibleTestResults = useMemo(
    () => (isReady && token ? testResults : []),
    [isReady, token, testResults]
  );
  const generatedBugs = useMemo(() => generateBugsFromTests(visibleTestResults), [visibleTestResults]);
  const bugs = useMemo(() => (isReady && token ? [...manualBugs, ...generatedBugs] : []), [isReady, token, manualBugs, generatedBugs]);

  const addBug = useCallback((bug: Bug) => {
    setManualBugs((prev) => [bug, ...prev]);
  }, []);

  const updateBugStatus = useCallback((id: string, status: Bug["status"]) => {
    setManualBugs((prev) => prev.map((b) => (b.id === id ? { ...b, status } : b)));
  }, []);

  const addTestResult = useCallback((result: TestApiResponse) => {
    setTestResults((prev) => [result, ...prev]);
  }, []);

  const getBugById = useCallback(
    (id: string) => bugs.find((b) => b.id === id),
    [bugs]
  );

  const getTestById = useCallback(
    (id: string) => visibleTestResults.find((t) => t.test_id === id),
    [visibleTestResults]
  );

  const stats: DashboardStats = {
    totalTests: visibleTestResults.length,

    passed: visibleTestResults.filter(
      (t) => t.overall_status === "pass"
    ).length,

    failed: visibleTestResults.filter(
      (t) => t.overall_status === "fail"
    ).length,

    openBugs: bugs.filter(
      (b) => b.status === "open" || b.status === "in-progress"
    ).length,
  };

  return (
    <BugContext.Provider
      value={{ bugs, testResults, aiFindings, stats, addBug, updateBugStatus, addTestResult, getBugById, getTestById }}
    >
      {children}
    </BugContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────

export function useBugContext() {
  const ctx = useContext(BugContext);
  if (!ctx) throw new Error("useBugContext must be used within BugProvider");
  return ctx;
}
