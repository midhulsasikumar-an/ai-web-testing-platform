"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { BugDetailCard } from "@/components/bugs/bug-detail-card";
import { BugDialog } from "@/components/bugs/bug-dialog";
import { useBugContext } from "@/context/bug-context";
import { ArrowLeft, AlertTriangle, RefreshCw, Play } from "lucide-react";

export default function BugDetailPage() {
  const params = useParams();
  const { getBugById } = useBugContext();
  const bug = getBugById(params.id as string);

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
      <Header title={bug.title}>
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
        <span className="text-blue-500 font-mono font-medium">{bug.id}</span>
        <span>·</span>
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
