"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { BugDetailCard } from "@/components/bugs/bug-detail-card";
import { BugDialog } from "@/components/bugs/bug-dialog";
import { useBugContext } from "@/context/bug-context";
import { useAuth } from "@/context/auth-context";
import { getBugById as fetchBugById } from "@/services/bugs-api";
import type { Bug } from "@/types";
import { truncateText } from "@/lib/test-display";
import { ArrowLeft, AlertTriangle, RefreshCw, Play } from "lucide-react";

export default function BugDetailPage() {
  const params = useParams();
  const { token } = useAuth();
  const { getBugById } = useBugContext();
  const contextBug = getBugById(params.id as string);
  const [remoteBug, setRemoteBug] = useState<Bug | null>(null);
  const [loadingRemote, setLoadingRemote] = useState(false);

  useEffect(() => {
    const bugId = String(params.id || "");
    if (!bugId || contextBug || !token) {
      return;
    }

    let active = true;
    setLoadingRemote(true);

    fetchBugById(bugId, token)
      .then((raw) => {
        if (!active) {
          return;
        }

        const description = String(raw.bug_description || raw.description || "No details provided").trim();
        const fallbackName = String(raw.bug_name || raw.issue_type || raw.failed_step_name || raw.failed_step || raw.title || "General Issue").trim();
        const mapped: Bug = {
          id: String(raw.bug_id || bugId),
          title: truncateText(fallbackName || "General Issue", 50),
          bug_name: truncateText(fallbackName || "General Issue", 50),
          description,
          bug_description: description,
          severity: (raw.severity as Bug["severity"]) || "medium",
          status: (raw.status as Bug["status"]) || "open",
          url: String(raw.url || ""),
          createdAt: String(raw.created_at || new Date().toISOString()),
          steps: [],
          test_id: raw.test_id,
          test_name: raw.test_name,
        };
        setRemoteBug(mapped);
      })
      .catch((error) => {
        console.error("Failed to fetch bug detail by id:", error);
      })
      .finally(() => {
        if (active) {
          setLoadingRemote(false);
        }
      });

    return () => {
      active = false;
    };
  }, [params.id, contextBug, token]);

  const bug = contextBug ?? remoteBug;

  if (!bug && loadingRemote) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <p className="text-slate-400 text-sm">Loading bug details...</p>
      </div>
    );
  }

  if (!bug) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <p className="text-slate-400 text-sm">Bug not found.</p>
        <Link
          href="/bugs"
          className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Bug Tracker
        </Link>
      </div>
    );
  }

  // severity → badge style
  const severityBadge =
    bug.severity === "critical" || bug.severity === "high"
      ? "bg-red-100 text-red-600 border-red-200"
      : bug.severity === "medium"
      ? "bg-yellow-100 text-yellow-700 border-yellow-200"
      : "bg-blue-100 text-blue-600 border-blue-200";

  // extract domain
  let domain = bug.url;
  try {
    domain = new URL(bug.url.startsWith("http") ? bug.url : `https://${bug.url}`).hostname.replace("www.", "");
  } catch { /* keep raw */ }

  return (
    <>
      {/* ── Top breadcrumb + title header ── */}
      <Header title={bug.bug_name || bug.title}>
        {/* badges */}
        <span className={`hidden sm:inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${severityBadge}`}>
          <AlertTriangle className="h-3 w-3" />
          {bug.severity.charAt(0).toUpperCase() + bug.severity.slice(1)} Priority
        </span>

        {bug.status === "open" || bug.status === "in-progress" ? (
          <span className="hidden sm:inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
            <RefreshCw className="h-3 w-3" />
            Regression
          </span>
        ) : null}

        <Link
          href="/run-test"
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm font-semibold transition-colors shadow-sm"
        >
          <Play className="h-3.5 w-3.5" />
          Open Test Run
        </Link>

        <BugDialog bug={bug} />
      </Header>

      {/* ── breadcrumb ── */}
      <div className="px-6 pt-1 pb-3 flex items-center gap-1.5 text-xs text-slate-400">
        <a
          href={bug.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:underline"
        >
          {domain}
        </a>
      </div>

      {/* ── main detail ── */}
      <BugDetailCard bug={bug} />
    </>
  );
}
