"use client";

import { useState } from "react";
import Link from "next/link";
import type { Bug } from "@/types";
import { useBugContext } from "@/context/bug-context";
import { formatDate, formatTime24 } from "@/lib/formatters";
import { resolveTestDisplayName, truncateText } from "@/lib/test-display";
import { apiFetch, ApiHttpError } from "@/services/http";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BrainCircuit, MapPin,
  Circle, Monitor, User, GitBranch,
  Globe, Hash, RotateCcw, Wand2, Eye, Check, Loader2,
} from "lucide-react";

interface BugDetailCardProps {
  bug: Bug;
}

function SeverityBadge({ severity }: { severity: Bug["severity"] }) {
  const map: Record<Bug["severity"], string> = {
    critical: "bg-red-50 text-red-600 border-red-200",
    high:     "bg-orange-50 text-orange-600 border-orange-200",
    medium:   "bg-amber-50 text-amber-700 border-amber-200",
    low:      "bg-blue-50 text-blue-600 border-blue-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${map[severity]}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

export function BugDetailCard({ bug }: BugDetailCardProps) {
  const { getTestById, updateBugStatus } = useBugContext();
  const linkedTest = bug.test_id ? getTestById(bug.test_id) : undefined;

  const isResolved = bug.status === "resolved" || bug.status === "closed";
  const [resolving, setResolving] = useState(false);
  const [resolutionError, setResolutionError] = useState<string | null>(null);

  const [fixPlan, setFixPlan] = useState<{ summary: string; recommendations: string[] } | null>(null);
  const [generatingFix, setGeneratingFix] = useState(false);
  const [fixError, setFixError] = useState<string | null>(null);

  const handleMarkResolved = async () => {
    if (isResolved || resolving) return;
    setResolving(true);
    setResolutionError(null);
    try {
      const response = await apiFetch(
        `/api/bugs/${encodeURIComponent(bug.id)}/status`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "resolved" }),
        },
      );
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail?.detail || `Failed to mark bug as resolved (HTTP ${response.status})`);
      }
      updateBugStatus(bug.id, "resolved");
    } catch (error) {
      if (error instanceof ApiHttpError) {
        try {
          const parsed = JSON.parse(error.body);
          setResolutionError(parsed?.detail || error.message);
        } catch {
          setResolutionError(error.message);
        }
      } else {
        setResolutionError(error instanceof Error ? error.message : "Failed to mark as resolved");
      }
    } finally {
      setResolving(false);
    }
  };

  const handleGenerateFix = async () => {
    if (generatingFix) return;
    setGeneratingFix(true);
    setFixError(null);
    try {
      const response = await apiFetch(
        `/api/bugs/${encodeURIComponent(bug.id)}/generate-fix`,
        { method: "POST" },
      );
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail?.detail || `Failed to generate fix (HTTP ${response.status})`);
      }
      const data = await response.json();
      setFixPlan({
        summary: String(data.summary || "AI fix plan generated."),
        recommendations: Array.isArray(data.recommendations) ? data.recommendations.map(String) : [],
      });
    } catch (error) {
      if (error instanceof ApiHttpError) {
        try {
          const parsed = JSON.parse(error.body);
          setFixError(parsed?.detail || error.message);
        } catch {
          setFixError(error.message);
        }
      } else {
        setFixError(error instanceof Error ? error.message : "Failed to generate fix");
      }
    } finally {
      setGeneratingFix(false);
    }
  };

  let domain = bug.url;
  try {
    domain = new URL(bug.url.startsWith("http") ? bug.url : `https://${bug.url}`).hostname.replace("www.", "");
  } catch { /* keep raw */ }

  const evidenceScreenshot = typeof bug.evidence?.screenshot_path === "string" ? bug.evidence.screenshot_path : null;
  const evidenceScreenshots = Array.isArray(bug.evidence?.screenshots)
    ? (bug.evidence.screenshots.filter((item): item is string => typeof item === "string" && item.length > 0))
    : [];
  const screenshotUrl = evidenceScreenshot ?? evidenceScreenshots[0] ?? linkedTest?.screenshot?.home ?? null;

  const failedSteps = linkedTest?.results?.filter((r) => r.status === "fail").length ?? 0;
  const totalSteps  = linkedTest?.results?.length ?? 1;
  const stabilityIdx = Math.max(5, Math.round((1 - failedSteps / totalSteps) * 100));

  const occurrences  = linkedTest?.summary?.failed ?? failedSteps;
  const regressions  = linkedTest?.insights?.critical?.length ?? 0;

  const daysOpen = Math.ceil((new Date().getTime() - new Date(bug.createdAt).getTime()) / 86_400_000);

  const lifecycleEvents = bug.logs?.slice(0, 4).map((l) => ({
    label: l.level === "error" ? "Detected" : l.level === "warn" ? "Warning" : "Info",
    detail: l.message,
    date:   formatTime24(l.timestamp),
    type:   l.level as string,
  })) ?? [
    { label: "Detected", detail: `Bug first detected - ${bug.bug_name || bug.title}`, date: formatDate(bug.createdAt), type: "error" },
  ];

  return (
    <div className="flex flex-col gap-4 lg:flex-row">

      <div className="flex-1 flex flex-col gap-5">

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-3">
              <CardTitle>Bug Summary</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500">SEVERITY</span>
                <SeverityBadge severity={bug.severity} />
                <span className="text-xs font-medium text-slate-500 ml-2">TYPE</span>
                <span className="inline-flex items-center rounded-full border border-border bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {bug.test_id ? "E2E Flow" : "Manual"}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="text-sm text-slate-600 leading-relaxed">{bug.description}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
              <div>
                <p className="text-eyebrow mb-1">Detection Date</p>
                <p className="text-sm font-medium text-slate-700">{formatDate(bug.createdAt)}</p>
              </div>
              <div>
                <p className="text-eyebrow mb-1">URL Path</p>
                <p className="text-sm font-medium text-slate-700 truncate max-w-[120px]" title={bug.url}>
                  {bug.url.replace(/^https?:\/\/[^/]+/, "") || "/"}
                </p>
              </div>
              <div>
                <p className="text-eyebrow mb-1">AI Confidence</p>
                <p className="text-sm font-semibold text-primary">{stabilityIdx}% Accuracy</p>
              </div>
              <div>
                <p className="text-eyebrow mb-1">Last Seen</p>
                <p className="text-sm font-medium text-slate-700">
                  {linkedTest ? "During last run" : "At detection"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-primary">
              <BrainCircuit className="h-4 w-4" />
              AI Root Cause Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-eyebrow">Likely Cause</p>
                  <span className="text-[10px] font-bold bg-blue-200 text-blue-700 rounded-full px-1.5 py-0.5 uppercase tracking-wide">
                    High Confidence
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed line-clamp-4">{bug.description}</p>
              </div>
              <div className="rounded-lg border border-border bg-slate-50 p-3">
                <p className="text-eyebrow mb-1.5">Affected Area</p>
                <p className="text-sm font-semibold text-slate-800 capitalize">{domain}</p>
              </div>
              <div className="rounded-lg border border-border bg-slate-50 p-3">
                <p className="text-eyebrow mb-1.5">Confidence</p>
                <p className="text-sm font-semibold text-slate-800">{stabilityIdx}%</p>
              </div>
            </div>

            {(linkedTest?.recommendations?.[0] || bug.steps?.[0]) && (
              <div className="flex gap-2.5 rounded-lg border border-blue-100 bg-blue-50/60 p-3.5">
                <MapPin className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Suggested Fix</p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {linkedTest?.recommendations?.[0] ?? bug.steps?.[0]}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <Monitor className="h-4 w-4 text-slate-500" />
              Screenshot Evidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            {screenshotUrl ? (
              <div className="space-y-3">
                <div className="rounded-lg overflow-hidden border border-border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={screenshotUrl} alt="Screenshot evidence" className="w-full object-cover max-h-72" />
                </div>
                {evidenceScreenshots.length > 1 && (
                  <div className="flex flex-wrap gap-2">
                    {evidenceScreenshots.map((shot, index) => (
                      <a key={`${shot}-${index}`} href={shot} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">
                        Evidence {index + 1}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-slate-50 flex flex-col items-center justify-center gap-3 py-14 text-center">
                <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
                  <Monitor className="h-6 w-6 text-slate-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Screenshots captured during automated runs</p>
                  <p className="text-xs text-slate-400 mt-1">Re-run the test to capture fresh screenshots</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Bug Lifecycle</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 relative pl-5">
              <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-slate-100" />
              {lifecycleEvents.map((ev, i) => (
                <div key={i} className="relative flex gap-3 items-start">
                  <div className={`absolute -left-5 mt-0.5 w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                    ev.type === "error" ? "bg-red-500 border-red-500" :
                    ev.type === "warn"  ? "bg-amber-400 border-amber-400" :
                    ev.type === "success" ? "bg-emerald-500 border-emerald-500" :
                    "bg-primary border-primary"
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
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Related Test Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {linkedTest ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-2 text-left text-eyebrow">TEST NAME</th>
                    <th className="pb-2 text-left text-eyebrow">DATE</th>
                    <th className="pb-2 text-left text-eyebrow">STATUS</th>
                    <th className="pb-2 text-left text-eyebrow">RESULT</th>
                    <th className="pb-2 text-left text-eyebrow">ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-border/60 last:border-b-0">
                    <td className="py-3 text-xs text-primary font-medium">{truncateText(resolveTestDisplayName(linkedTest), 65)}</td>
                    <td className="py-3 text-xs text-slate-600">{linkedTest.created_at ? formatDate(linkedTest.created_at) : "—"}</td>
                    <td className="py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${
                        linkedTest.overall_status === "fail" ? "bg-red-50 text-red-600 border-red-200" :
                        linkedTest.overall_status === "pass" ? "bg-emerald-50 text-emerald-600 border-emerald-200" :
                        "bg-amber-50 text-amber-700 border-amber-200"
                      }`}>
                        {linkedTest.overall_status ?? linkedTest.status}
                      </span>
                    </td>
                    <td className="py-3 text-xs text-slate-600">
                      {linkedTest.summary ? `${linkedTest.summary.failed} failed, ${linkedTest.summary.passed} passed` : "—"}
                    </td>
                    <td className="py-3">
                      <Link href={`/test-history/${linkedTest.test_id}`} className="text-primary hover:opacity-80">
                        <Eye className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-slate-400">No linked test run available.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="lg:w-72 flex flex-col gap-4">

        <Card className="border-red-200">
          <CardContent className="space-y-3 py-4">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
              <h3 className="text-sm font-bold text-red-600 uppercase tracking-wide">Active Regression</h3>
            </div>
            <p className="text-muted-sm">Detected in latest run</p>

            <div>
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
              onClick={handleMarkResolved}
              disabled={isResolved || resolving}
              className={`w-full py-2 rounded-lg border text-sm font-semibold transition-colors flex items-center justify-center gap-2 ${
                isResolved
                  ? "border-emerald-200 bg-emerald-50 text-emerald-600 cursor-default"
                  : resolving
                  ? "border-slate-300 bg-slate-100 text-slate-500 cursor-progress"
                  : "border-red-300 bg-white text-red-600 hover:bg-red-50"
              }`}
              aria-live="polite"
            >
              {resolving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : isResolved ? (
                <>
                  <Check className="h-4 w-4" />
                  Marked as Resolved
                </>
              ) : (
                "Mark as Resolved"
              )}
            </button>
            {resolutionError ? (
              <p role="alert" className="mt-2 text-xs text-red-600">
                {resolutionError}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetaRow icon={User} label="Assigned To" value={bug.assignedTo ?? "AI Pilot"} />
            <MetaRow icon={Hash} label="Project" value={linkedTest?.project ?? domain} />
            <MetaRow icon={GitBranch} label="Branch" value={linkedTest?.test_type ?? "main"} />
            <MetaRow icon={Globe} label="Browsers" value={bug.environment ?? "Chromium"} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="grid grid-cols-2 gap-3">
              <StatBox label="Occurrences" value={occurrences} />
              <StatBox label="Regressions" value={regressions} />
              <StatBox label="Days Open" value={daysOpen} />
              <StatBox label="Affected Runs" value={linkedTest?.summary?.total ?? failedSteps} />
            </div>
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="space-y-3 py-4">
            <h3 className="text-sm font-semibold text-slate-800">Fix it now?</h3>
            <p className="text-muted-sm">
              AI can propose a remediation plan for this specific issue.
            </p>
            <button
              type="button"
              onClick={handleGenerateFix}
              disabled={generatingFix}
              className={`w-full py-2 rounded-lg text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${
                generatingFix ? "bg-slate-400 cursor-progress" : "bg-primary hover:bg-primary/90"
              }`}
            >
              {generatingFix ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <Wand2 className="h-4 w-4" />
                  Generate Fix with AI
                </>
              )}
            </button>
            {fixError ? (
              <p role="alert" className="text-xs text-red-600">
                {fixError}
              </p>
            ) : null}
            {fixPlan ? (
              <div className="rounded-lg border border-blue-200 bg-white p-3 text-xs text-slate-700">
                <p className="font-semibold text-slate-800">Recommended plan</p>
                <p className="mt-1 text-slate-600">{fixPlan.summary}</p>
                {fixPlan.recommendations.length > 0 ? (
                  <ol className="mt-2 list-decimal space-y-1 pl-4 text-slate-600">
                    {fixPlan.recommendations.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Link
          href="/bugs"
          className="flex items-center justify-center gap-1.5 text-xs text-slate-400 hover:text-primary transition-colors mt-1"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Back to Bug Tracker
        </Link>
      </div>
    </div>
  );
}

function MetaRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center shrink-0">
        <Icon className="h-3.5 w-3.5 text-slate-500" />
      </div>
      <div>
        <p className="text-eyebrow">{label}</p>
        <p className="text-xs font-medium text-slate-700 truncate max-w-[160px]">{value}</p>
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-slate-50 p-3 text-center">
      <p className="text-lg font-bold text-slate-800">{value}</p>
      <p className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</p>
    </div>
  );
}
