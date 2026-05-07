// ── Bug generation utilities ───────────────────────────────────────
// Moved from context/bug-context.tsx to separate business logic from state.

import type { Bug, BugSeverity } from "@/types";
import { sampleBugs } from "@/lib/data";

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
      {
        timestamp: new Date().toISOString(),
        level: "info",
        message: `AI scan initiated for ${url}`,
      },
      {
        timestamp: new Date().toISOString(),
        level: "error",
        message: `Issue detected: ${bugDescriptions[idx]}`,
      },
    ],
  };
}
