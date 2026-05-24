"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useMemo } from "react";
import type { Bug, DashboardStats, AIFinding } from "@/types";
import {sampleAIFindings } from "@/lib/data";
import { getAllTests } from "@/services/test-api";
import type { TestApiResponse } from "@/services/test-api";
import { getAllBugs, type BugApiResponse } from "@/services/bugs-api";
import { truncateText } from "@/lib/test-display";
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
  const [backendBugs, setBackendBugs] = useState<Bug[]>([]);
  const [testResults, setTestResults] = useState<TestApiResponse[]>([]);
  const [aiFindings] = useState<AIFinding[]>(sampleAIFindings);

  const mapBugSeverity = useCallback((value?: string): Bug["severity"] => {
    const normalized = (value ?? "").toLowerCase();
    if (normalized === "critical" || normalized === "high" || normalized === "medium" || normalized === "low") {
      return normalized;
    }
    return "medium";
  }, []);

  const mapBugStatus = useCallback((value?: string): Bug["status"] => {
    const normalized = (value ?? "").toLowerCase();
    if (normalized === "open" || normalized === "in-progress" || normalized === "resolved" || normalized === "closed") {
      return normalized;
    }
    return "open";
  }, []);

  const toBug = useCallback((raw: BugApiResponse): Bug => {
    const normalizeIssueType = (value?: string): string => {
      const text = String(value || "").trim();
      if (!text) {
        return "";
      }
      return text
        .replace(/[_-]+/g, " ")
        .split(" ")
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(" ");
    };

    const generateShortTitle = (text: string): string => {
      const lowered = text.toLowerCase();
      if (/(button|click)/.test(lowered)) return "Button Interaction Failure";
      if (/(link|navigate|navigation|redirect)/.test(lowered)) return "Link Navigation Failure";
      if (/(validation|invalid|required|input)/.test(lowered)) return "Input Validation Failure";
      if (/(load|timeout|network|page)/.test(lowered)) return "Page Load Failure";
      if (/(missing|not found|locator)/.test(lowered)) return "Missing Element";
      if (/(screenshot|visual|pixel)/.test(lowered)) return "Screenshot Mismatch";
      if (/(accessibility|aria|contrast|a11y)/.test(lowered)) return "Accessibility Issue";
      if (/(performance|slow|latency)/.test(lowered)) return "Performance Issue";
      if (/(login|auth|credential|password)/.test(lowered)) return "Login Failure";
      if (/(form|submit|submission)/.test(lowered)) return "Form Submission Failure";
      return "General Issue";
    };

    const priorityName = (
      String(raw.bug_name || "").trim() ||
      normalizeIssueType(raw.issue_type) ||
      String(raw.failed_step_name || raw.failed_step || raw.title || "").trim() ||
      generateShortTitle(String(raw.bug_description || raw.description || raw.title || "")) ||
      "General Issue"
    );

    const name = priorityName;
    const description = String(raw.bug_description || raw.description || "No details provided").trim();
    const bugName = truncateText(name || "Detected issue", 50);

    return {
      id: String(raw.bug_id || raw.execution_id || raw.test_id || `${bugName}-${raw.created_at || Date.now()}`),
      title: bugName,
      bug_name: bugName,
      description,
      bug_description: description,
      severity: mapBugSeverity(raw.severity),
      status: mapBugStatus(raw.status),
      url: String(raw.url || ""),
      createdAt: String(raw.created_at || new Date().toISOString()),
      steps: [],
      test_id: raw.test_id,
      test_name: raw.test_name,
    };
  }, [mapBugSeverity, mapBugStatus]);

  useEffect(() => {
    if (!isReady || !token) {
      return;
    }

    let active = true;

    async function loadTests() {
      try {
        const [tests, bugs] = await Promise.all([
          getAllTests(token ?? undefined),
          getAllBugs(token ?? undefined),
        ]);

        if (active) {
          setTestResults(tests);
          setBackendBugs(bugs.map(toBug));
        }
      } catch (error) {
        console.error("Failed to load tests/bugs:", error);
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
  const bugs = useMemo(() => (isReady && token ? backendBugs : []), [isReady, token, backendBugs]);

  const addBug = useCallback((bug: Bug) => {
    setBackendBugs((prev) => [bug, ...prev]);
  }, []);

  const updateBugStatus = useCallback((id: string, status: Bug["status"]) => {
    setBackendBugs((prev) => prev.map((b) => (b.id === id ? { ...b, status } : b)));
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
