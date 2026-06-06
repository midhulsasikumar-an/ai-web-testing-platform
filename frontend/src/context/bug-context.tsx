"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { Bug, DashboardStats, AIFinding } from "@/types";
import {sampleAIFindings } from "@/lib/data";
import { getAllTests } from "@/services/test-api";
import type { TestApiResponse } from "@/services/test-api";
import { generateBugsFromTests } from "@/lib/bug-generators";

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
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [testResults, setTestResults] = useState<TestApiResponse[]>([]);
  const [aiFindings] = useState<AIFinding[]>(sampleAIFindings);
  useEffect(() => {
    async function loadTests() {
      try {
        const tests = await getAllTests();

        setTestResults(tests);
      } catch (error) {
        console.error("Failed to load tests:", error);
      }
    }

    loadTests();
  }, []);

  useEffect(() => {
    const generatedBugs = generateBugsFromTests(testResults);

    setBugs(generatedBugs);
  }, [testResults]);

  const addBug = useCallback((bug: Bug) => {
    setBugs((prev) => [bug, ...prev]);
  }, []);

  const updateBugStatus = useCallback((id: string, status: Bug["status"]) => {
    setBugs((prev) => prev.map((b) => (b.id === id ? { ...b, status } : b)));
  }, []);

  const addTestResult = useCallback((result: TestApiResponse) => {
    setTestResults((prev) => [result, ...prev]);
  }, []);

  const getBugById = useCallback(
    (id: string) => bugs.find((b) => b.id === id),
    [bugs]
  );

  const getTestById = useCallback(
    (id: string) => testResults.find((t) => t.test_id === id),
    [testResults]
  );

  const stats: DashboardStats = React.useMemo(() => ({
    totalTests: testResults.length,

    passed: testResults.filter(
      (t) => t.overall_status === "pass"
    ).length,

    failed: testResults.filter(
      (t) => t.overall_status === "fail"
    ).length,

    openBugs: bugs.filter(
      (b) => b.status === "open" || b.status === "in-progress"
    ).length,
  }), [testResults, bugs]);

  const contextValue = React.useMemo(() => ({
    bugs, testResults, aiFindings, stats, addBug, updateBugStatus, addTestResult, getBugById, getTestById
  }), [bugs, testResults, aiFindings, stats, addBug, updateBugStatus, addTestResult, getBugById, getTestById]);

  return (
    <BugContext.Provider
      value={contextValue}
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
