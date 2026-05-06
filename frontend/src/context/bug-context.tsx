"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import type { Bug, TestResult, DashboardStats, AIFinding } from "@/types";
import { sampleBugs, sampleTestResults, sampleAIFindings } from "@/lib/data";

// ── Context shape ──────────────────────────────────────────────────

interface BugContextType {
  bugs: Bug[];
  testResults: TestResult[];
  aiFindings: AIFinding[];
  stats: DashboardStats;
  addBug: (bug: Bug) => void;
  updateBugStatus: (id: string, status: Bug["status"]) => void;
  addTestResult: (result: TestResult) => void;
  getBugById: (id: string) => Bug | undefined;
  getTestById: (id: string) => TestResult | undefined;
}

const BugContext = createContext<BugContextType | undefined>(undefined);

// ── Provider ───────────────────────────────────────────────────────

export function BugProvider({ children }: { children: React.ReactNode }) {
  const [bugs, setBugs] = useState<Bug[]>(sampleBugs);
  const [testResults, setTestResults] = useState<TestResult[]>(sampleTestResults);
  const [aiFindings] = useState<AIFinding[]>(sampleAIFindings);

  const addBug = useCallback((bug: Bug) => {
    setBugs((prev) => [bug, ...prev]);
  }, []);

  const updateBugStatus = useCallback((id: string, status: Bug["status"]) => {
    setBugs((prev) => prev.map((b) => (b.id === id ? { ...b, status } : b)));
  }, []);

  const addTestResult = useCallback((result: TestResult) => {
    setTestResults((prev) => [result, ...prev]);
  }, []);

  const getBugById = useCallback(
    (id: string) => bugs.find((b) => b.id === id),
    [bugs]
  );

  const getTestById = useCallback(
    (id: string) => testResults.find((t) => t.id === id),
    [testResults]
  );

  const baseTotal = 1284;
  const basePassed = 1150;
  const baseFailed = 134;

  const stats: DashboardStats = {
    totalTests: baseTotal + testResults.length,
    passed: basePassed + testResults.filter((t) => t.status === "passed").length,
    failed: baseFailed + testResults.filter((t) => t.status === "failed").length,
    openBugs: bugs.filter((b) => b.status === "open" || b.status === "in-progress").length,
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
