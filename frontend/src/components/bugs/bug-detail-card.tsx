"use client";

import { useState } from "react";
import Link from "next/link";
import type { Bug } from "@/types";
import { useBugContext } from "@/context/bug-context";
import { formatDate, formatTime24 } from "@/lib/formatters";
import {
  BrainCircuit, MapPin,
  Circle, Monitor, User, GitBranch,
  Globe, Hash, RotateCcw, Wand2, Eye,
} from "lucide-react";

interface BugDetailCardProps {
  bug: Bug;
}

// ── inline badge helpers ───────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: Bug["severity"] }) {
  const map: Record<Bug["severity"], string> = {
    critical: "bg-red-100 text-red-700 border-red-200",
    high:     "bg-orange-100 text-orange-700 border-orange-200",
    medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
    low:      "bg-blue-100 text-blue-700 border-blue-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${map[severity]}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}



// ── main export ────────────────────────────────────────────────────────────

export function BugDetailCard({ bug }: BugDetailCardProps) {
  const { getTestById } = useBugContext();
  const linkedTest = bug.test_id ? getTestById(bug.test_id) : undefined;

  const [resolved, setResolved] = useState(bug.status === "resolved" || bug.status === "closed");

  // derive domain from url
  let domain = bug.url;
  try {
    domain = new URL(bug.url.startsWith("http") ? bug.url : `https://${bug.url}`).hostname.replace("www.", "");
  } catch { /* keep raw */ }

  // screenshot from linked test
  const screenshotUrl = linkedTest?.screenshot?.home ?? null;

  // stability index — inferred from how many test steps failed
  const failedSteps = linkedTest?.results?.filter((r) => r.status === "fail").length ?? 0;
  const totalSteps  = linkedTest?.results?.length ?? 1;
  const stabilityIdx = Math.max(5, Math.round((1 - failedSteps / totalSteps) * 100));

  // occurrences / regressions from test summary
  const occurrences  = linkedTest?.summary?.failed ?? failedSteps;
  const regressions  = linkedTest?.insights?.critical?.length ?? 0;

  // days open — computed outside JSX to avoid impure-function lint rule
  const daysOpen = Math.ceil((new Date().getTime() - new Date(bug.createdAt).getTime()) / 86_400_000);

  // build a timeline from logs if present
  const lifecycleEvents = bug.logs?.slice(0, 4).map((l) => ({
    label: l.level === "error" ? "Detected" : l.level === "warn" ? "Warning" : "Info",
    detail: l.message,
    date:   formatTime24(l.timestamp),
    type:   l.level as string,
  })) ?? [
    { label: "Detected", detail: `Bug first detected — ${bug.title}`, date: formatDate(bug.createdAt), type: "error" },
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-5 px-6 pb-10">

      {/* ════════════════════════════════════════════
          LEFT COLUMN — main detail
      ════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col gap-5">

        {/* ── Bug Summary ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
          <div className="flex items-start justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-800">Bug Summary</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">SEVERITY</span>
              <SeverityBadge severity={bug.severity} />
              <span className="text-xs font-medium text-slate-500 ml-2">TYPE</span>
              <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
                {bug.test_id ? "E2E Flow" : "Manual"}
              </span>
            </div>
          </div>

          <p className="text-sm text-slate-600 leading-relaxed mb-5">{bug.description}</p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100">
            <div>
              <p className="text-xs text-slate-400 mb-1">Detection Date</p>
              <p className="text-sm font-medium text-slate-700">{formatDate(bug.createdAt)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">URL Path</p>
              <p className="text-sm font-medium text-slate-700 truncate max-w-[120px]" title={bug.url}>
                {bug.url.replace(/^https?:\/\/[^/]+/, "") || "/"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">AI Confidence</p>
              <p className="text-sm font-semibold text-blue-600">{stabilityIdx}% Accuracy</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Last Seen</p>
              <p className="text-sm font-medium text-slate-700">
                {linkedTest ? "During last run" : "At detection"}
              </p>
            </div>
          </div>
        </section>

        {/* ── AI Root Cause Analysis ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-blue-600 mb-4">
            <BrainCircuit className="h-4 w-4" />
            AI Root Cause Analysis
          </h2>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-medium text-slate-500">Likely Cause</p>
                <span className="text-[10px] font-bold bg-blue-200 text-blue-700 rounded-full px-1.5 py-0.5 uppercase tracking-wide">
                  High Confidence
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed line-clamp-4">{bug.description}</p>
            </div>
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <p className="text-xs font-medium text-slate-500 mb-1.5">Affected Area</p>
              <p className="text-sm font-semibold text-slate-800 capitalize">{domain}</p>
            </div>
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <p className="text-xs font-medium text-slate-500 mb-1.5">Confidence</p>
              <p className="text-sm font-semibold text-slate-800">{stabilityIdx}%</p>
            </div>
          </div>

          {/* Suggested Fix */}
          {(linkedTest?.recommendations?.[0] || bug.steps?.[0]) && (
            <div className="flex gap-2.5 rounded-lg border border-blue-100 bg-blue-50/60 p-3.5">
              <MapPin className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-slate-700 mb-1">Suggested Fix</p>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {linkedTest?.recommendations?.[0] ?? bug.steps?.[0]}
                </p>
              </div>
            </div>
          )}
        </section>

        {/* ── Screenshot Evidence ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-800 mb-4">
            <Monitor className="h-4 w-4 text-slate-500" />
            Screenshot Evidence
          </h2>
          {screenshotUrl ? (
            <div className="rounded-lg overflow-hidden border border-slate-200">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={screenshotUrl} alt="Screenshot evidence" className="w-full object-cover max-h-72" />
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-3 py-14 text-center">
              <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
                <Monitor className="h-6 w-6 text-slate-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-500">Screenshots captured during automated runs</p>
                <p className="text-xs text-slate-400 mt-1">Re-run the test to capture fresh screenshots</p>
              </div>
            </div>
          )}
        </section>

        {/* ── Bug Lifecycle ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
          <h2 className="text-base font-semibold text-slate-800 mb-4">Bug Lifecycle</h2>
          <div className="flex flex-col gap-4 relative pl-5">
            {/* vertical line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-slate-100" />
            {lifecycleEvents.map((ev, i) => (
              <div key={i} className="relative flex gap-3 items-start">
                <div className={`absolute -left-5 mt-0.5 w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  ev.type === "error" ? "bg-red-500 border-red-500" :
                  ev.type === "warn"  ? "bg-amber-400 border-amber-400" :
                  ev.type === "success" ? "bg-teal-500 border-teal-500" :
                  "bg-blue-400 border-blue-400"
                }`}>
                  <Circle className="h-1.5 w-1.5 text-white fill-white" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">{ev.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{ev.detail}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{ev.date}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Related Test Runs ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
          <h2 className="text-base font-semibold text-slate-800 mb-4">Related Test Runs</h2>
          {linkedTest ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="pb-2 text-left text-xs font-medium text-slate-500">RUN ID</th>
                  <th className="pb-2 text-left text-xs font-medium text-slate-500">DATE</th>
                  <th className="pb-2 text-left text-xs font-medium text-slate-500">STATUS</th>
                  <th className="pb-2 text-left text-xs font-medium text-slate-500">RESULT</th>
                  <th className="pb-2 text-left text-xs font-medium text-slate-500">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                <tr>
                  <td className="py-3 font-mono text-xs text-blue-600">#{linkedTest.test_id.slice(0, 8)}</td>
                  <td className="py-3 text-xs text-slate-600">{linkedTest.created_at ? formatDate(linkedTest.created_at) : "—"}</td>
                  <td className="py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${
                      linkedTest.overall_status === "fail" ? "bg-red-50 text-red-600 border-red-200" :
                      linkedTest.overall_status === "pass" ? "bg-teal-50 text-teal-600 border-teal-200" :
                      "bg-amber-50 text-amber-600 border-amber-200"
                    }`}>
                      {linkedTest.overall_status ?? linkedTest.status}
                    </span>
                  </td>
                  <td className="py-3 text-xs text-slate-600">
                    {linkedTest.summary ? `${linkedTest.summary.failed} failed, ${linkedTest.summary.passed} passed` : "—"}
                  </td>
                  <td className="py-3">
                    <Link href={`/test-history/${linkedTest.test_id}`} className="text-blue-500 hover:text-blue-700">
                      <Eye className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-slate-400">No linked test run available.</p>
          )}
        </section>
      </div>

      {/* ════════════════════════════════════════════
          RIGHT COLUMN — sidebar
      ════════════════════════════════════════════ */}
      <div className="lg:w-72 flex flex-col gap-4">

        {/* ── Active Regression Status ── */}
        <section className="rounded-xl border border-red-200 bg-white shadow-sm p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <h3 className="text-sm font-bold text-red-600 uppercase tracking-wide">Active Regression</h3>
          </div>
          <p className="text-xs text-slate-500 mb-3">Detected in latest run</p>

          {/* Stability bar */}
          <div className="mb-4">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-500">Stability Index</span>
              <span className="font-semibold text-red-600">{100 - stabilityIdx}%</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-100">
              <div
                className="h-1.5 rounded-full bg-red-500 transition-all"
                style={{ width: `${100 - stabilityIdx}%` }}
              />
            </div>
          </div>

          <button
            onClick={() => setResolved(true)}
            disabled={resolved}
            className={`w-full py-2 rounded-lg border text-sm font-semibold transition-colors ${
              resolved
                ? "border-teal-200 bg-teal-50 text-teal-600 cursor-default"
                : "border-red-300 bg-white text-red-600 hover:bg-red-50"
            }`}
          >
            {resolved ? "✓ Marked as Resolved" : "Mark as Resolved"}
          </button>
        </section>

        {/* ── Metadata ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Metadata</h3>
          <div className="flex flex-col gap-3">
            <MetaRow icon={User} label="Assigned To" value={bug.assignedTo ?? "AI Pilot"} />
            <MetaRow icon={Hash} label="Project" value={linkedTest?.project ?? domain} />
            <MetaRow icon={GitBranch} label="Branch" value={linkedTest?.test_type ?? "main"} />
            <MetaRow
              icon={Globe}
              label="Browsers"
              value={bug.environment ?? "Chromium"}
            />
          </div>
        </section>

        {/* ── Stats ── */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
          <div className="grid grid-cols-2 gap-3">
            <StatBox label="Occurrences" value={occurrences} />
            <StatBox label="Regressions" value={regressions} />
            <StatBox label="Days Open" value={daysOpen} />
            <StatBox label="Affected Runs" value={linkedTest?.summary?.total ?? failedSteps} />
          </div>
        </section>

        {/* ── Fix it Now ── */}
        <section className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Fix it now?</h3>
          <p className="text-xs text-slate-500 mb-4">
            AI can attempt an automated fix for this specific issue.
          </p>
          <button className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors shadow-sm">
            <Wand2 className="h-4 w-4" />
            Generate Fix with AI
          </button>
        </section>

        {/* ── Back to list ── */}
        <Link
          href="/bugs"
          className="flex items-center justify-center gap-1.5 text-xs text-slate-400 hover:text-blue-600 transition-colors mt-1"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Back to Bug Tracker
        </Link>
      </div>
    </div>
  );
}

// ── small helpers ─────────────────────────────────────────────────────────

function MetaRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center shrink-0">
        <Icon className="h-3.5 w-3.5 text-slate-500" />
      </div>
      <div>
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-xs font-medium text-slate-700 truncate max-w-[160px]">{value}</p>
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-center">
      <p className="text-lg font-bold text-slate-800">{value}</p>
      <p className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</p>
    </div>
  );
}
