"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { Bug, TestResult, DashboardStats, BugSeverity, AIFinding } from "@/lib/types";
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
    setBugs((prev) =>
      prev.map((b) => (b.id === id ? { ...b, status } : b))
    );
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

  // Boosted stats to match the Stitch design's larger numbers
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

// ── Helpers ────────────────────────────────────────────────────────

const bugTitles = [
  "Broken layout on target page",
  "JavaScript error detected in console",
  "Missing alt text on images",
  "Slow page load time (>5s)",
  "Form submission returns 500 error",
  "Navigation link leads to 404",
  "CORS error on API request",
  "Unhandled promise rejection detected",
];

const bugDescriptions = [
  "The page layout breaks on certain viewport sizes causing elements to overlap.",
  "Multiple JavaScript errors were detected in the browser console during page load.",
  "Critical images on the page are missing alt attributes, affecting accessibility.",
  "The page took over 5 seconds to fully load, exceeding performance thresholds.",
  "Submitting the main form on the page results in a 500 Internal Server Error.",
  "A primary navigation link points to a route that returns a 404 Not Found page.",
  "API requests from the page are blocked by CORS policy, preventing data loading.",
  "An unhandled promise rejection was detected, which may cause silent failures.",
];

const teamMembers = ["Sarah Chen", "Mike Johnson", "Alex Rivera", "Lisa Park"];

export function generateBugFromUrl(url: string): Bug {
  const idx = Math.floor(Math.random() * bugTitles.length);
  const severities: BugSeverity[] = ["critical", "high", "medium", "low"];
  const severity = severities[Math.floor(Math.random() * severities.length)];
  const assignee = teamMembers[Math.floor(Math.random() * teamMembers.length)];

  const count = sampleBugs.length + Math.floor(Math.random() * 900) + 100;

  return {
    id: `BUG-${String(count).padStart(3, "0")}`,
    title: bugTitles[idx],
    description: bugDescriptions[idx],
    severity,
    status: "open",
    url,
    createdAt: new Date().toISOString(),
    assignedTo: assignee,
    environment: "Chrome 125, Auto-detected",
    steps: [
      `Navigate to ${url}`,
      "Wait for full page load",
      "Inspect page for visual/functional issues",
      "Check browser console for errors",
    ],
    logs: [
      { timestamp: new Date().toISOString(), level: "info", message: `AI scan initiated for ${url}` },
      { timestamp: new Date().toISOString(), level: "error", message: `Issue detected: ${bugDescriptions[idx]}` },
    ],
  };
}
