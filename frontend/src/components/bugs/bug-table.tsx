"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { Bug } from "@/types";
import { formatDate } from "@/lib/formatters";
import {
  Globe, AlertCircle, CheckCircle2, RefreshCw,
  Search, Eye, Plus, ChevronDown,
} from "lucide-react";

interface BugTableProps {
  bugs: Bug[];
}

// ── helpers ────────────────────────────────────────────────────────────────

function extractDomain(url: string): string {
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

function getFaviconUrl(url: string): string {
  const domain = extractDomain(url);
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
}

function lastTestedLabel(bugs: Bug[]): string {
  if (!bugs.length) return "—";
  const latest = bugs.reduce((a, b) =>
    new Date(a.createdAt) > new Date(b.createdAt) ? a : b
  );
  const diff = Date.now() - new Date(latest.createdAt).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

// ── sub-components ─────────────────────────────────────────────────────────

function SeverityPill({ severity }: { severity: Bug["severity"] }) {
  const map: Record<Bug["severity"], string> = {
    critical: "bg-red-50 text-red-600 border-red-200",
    high:     "bg-orange-50 text-orange-600 border-orange-200",
    medium:   "bg-yellow-50 text-yellow-600 border-yellow-200",
    low:      "bg-blue-50 text-blue-600 border-blue-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${map[severity]}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

function StatusPill({ status }: { status: Bug["status"] }) {
  const map: Record<Bug["status"], { cls: string; label: string }> = {
    open:        { cls: "text-red-500 font-semibold",  label: "Open" },
    "in-progress": { cls: "text-blue-500 font-semibold", label: "In Progress" },
    resolved:    { cls: "text-teal-500 font-semibold", label: "Resolved" },
    closed:      { cls: "text-slate-400 font-semibold", label: "Closed" },
  };
  const { cls, label } = map[status];
  return <span className={`text-sm ${cls}`}>{label}</span>;
}

// ── main component ─────────────────────────────────────────────────────────

export function BugTable({ bugs }: BugTableProps) {
  const [search, setSearch]     = useState("");
  const [filter, setFilter]     = useState<"All" | "Open" | "Resolved" | "Warning">("All");
  const [sortBy, setSortBy]     = useState("Most Recent");

  // ── stat card values ────────────────────────────────────────────────────
  const totalSites    = useMemo(() => new Set(bugs.map((b) => extractDomain(b.url))).size, [bugs]);
  const openCount     = useMemo(() => bugs.filter((b) => b.status === "open" || b.status === "in-progress").length, [bugs]);
  const resolvedCount = useMemo(() => bugs.filter((b) => b.status === "resolved" || b.status === "closed").length, [bugs]);
  const fixRate       = bugs.length > 0 ? Math.round((resolvedCount / bugs.length) * 100) : 0;

  // recurring = same domain appears in more than one open bug
  const domainOpenCount = useMemo(() => {
    const map: Record<string, number> = {};
    bugs.filter((b) => b.status === "open" || b.status === "in-progress").forEach((b) => {
      const d = extractDomain(b.url);
      map[d] = (map[d] ?? 0) + 1;
    });
    return map;
  }, [bugs]);
  const recurringCount = useMemo(
    () => Object.values(domainOpenCount).filter((c) => c > 1).length,
    [domainOpenCount]
  );

  // ── filtered bugs ───────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    let result = bugs;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (b) => b.title.toLowerCase().includes(q) || extractDomain(b.url).includes(q)
      );
    }
    if (filter === "Open")     result = result.filter((b) => b.status === "open" || b.status === "in-progress");
    if (filter === "Resolved") result = result.filter((b) => b.status === "resolved" || b.status === "closed");
    if (filter === "Warning")  result = result.filter((b) => b.severity === "medium" || b.severity === "low");
    if (sortBy === "Most Recent") result = [...result].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    if (sortBy === "Severity")    result = [...result].sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    });
    return result;
  }, [bugs, search, filter, sortBy]);

  // ── group by domain ────────────────────────────────────────────────────
  const grouped = useMemo(() => {
    const map = new Map<string, Bug[]>();
    filtered.forEach((b) => {
      const key = extractDomain(b.url);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(b);
    });
    return map;
  }, [filtered]);

  // ── render ─────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6 px-6 pb-8">

      {/* ── Stat Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Websites Tested */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col gap-3 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
              <Globe className="h-4 w-4 text-blue-500" />
            </div>
            <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
              +{Math.max(totalSites - 1, 0)} this week
            </span>
          </div>
          <div>
            <p className="text-xs text-slate-500">Total Websites Tested</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">{totalSites}</p>
          </div>
        </div>

        {/* Total Open Bugs */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col gap-3 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center">
              <AlertCircle className="h-4 w-4 text-red-500" />
            </div>
            <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
              High Priority
            </span>
          </div>
          <div>
            <p className="text-xs text-slate-500">Total Open Bugs</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">{openCount}</p>
          </div>
        </div>

        {/* Resolved Bugs */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col gap-3 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-teal-50 flex items-center justify-center">
              <CheckCircle2 className="h-4 w-4 text-teal-500" />
            </div>
            <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
              {fixRate}% rate
            </span>
          </div>
          <div>
            <p className="text-xs text-slate-500">Resolved Bugs</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">{resolvedCount}</p>
          </div>
        </div>

        {/* Recurring Bugs */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col gap-3 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center">
              <RefreshCw className="h-4 w-4 text-amber-500" />
            </div>
            <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
              Action needed
            </span>
          </div>
          <div>
            <p className="text-xs text-slate-500">Recurring Bugs</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">{recurringCount}</p>
          </div>
        </div>
      </div>

      {/* ── Search + Filter + Sort ────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search Bugs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
          />
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1">
          {(["All", "Open", "Resolved", "Warning"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                filter === f
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Sort */}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-slate-500 whitespace-nowrap">Sort by:</span>
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="appearance-none rounded-lg border border-slate-200 bg-white py-2 pl-3 pr-8 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/30 cursor-pointer"
            >
              <option>Most Recent</option>
              <option>Severity</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          </div>
        </div>
      </div>

      {/* ── Grouped Tables ────────────────────────────────────────────── */}
      {grouped.size === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white flex flex-col items-center justify-center py-16 text-center gap-3">
          <CheckCircle2 className="h-10 w-10 text-slate-300" />
          <p className="text-sm font-medium text-slate-500">No bugs found. Run a test to detect issues.</p>
        </div>
      ) : (
        Array.from(grouped.entries()).map(([domain, domainBugs]) => {
          const siteOpen     = domainBugs.filter((b) => b.status === "open" || b.status === "in-progress").length;
          const siteResolved = domainBugs.filter((b) => b.status === "resolved" || b.status === "closed").length;

          return (
            <div key={domain} className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
              {/* Site header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={getFaviconUrl(domainBugs[0].url)}
                    alt={domain}
                    width={28}
                    height={28}
                    className="rounded-md border border-slate-100 bg-slate-50 p-0.5"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%23f1f5f9' rx='6'/><text y='22' x='8' font-size='16'>🌐</text></svg>`;
                    }}
                  />
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{domain}</p>
                    <p className="text-xs text-slate-400">Last Tested: {lastTestedLabel(domainBugs)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-xs">
                  <div className="text-center">
                    <p className="text-slate-400 uppercase tracking-wide font-medium">Total</p>
                    <p className="font-bold text-slate-800 text-sm">{domainBugs.length}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-red-400 uppercase tracking-wide font-medium">Open</p>
                    <p className="font-bold text-red-500 text-sm">{siteOpen}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-blue-400 uppercase tracking-wide font-medium">Resolved</p>
                    <p className="font-bold text-blue-500 text-sm">{siteResolved}</p>
                  </div>
                </div>
              </div>

              {/* Bug rows */}
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60">
                    <th className="px-5 py-2.5 text-left text-xs font-medium text-slate-500">Bug Title</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 w-28">Severity</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 w-28">Status</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 w-36">Date Detected</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 w-20">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {domainBugs.map((bug) => (
                    <tr key={bug.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/bugs/${bug.id}`}
                          className="font-medium text-slate-800 hover:text-blue-600 hover:underline transition-colors line-clamp-1"
                        >
                          {bug.title}
                        </Link>
                      </td>
                      <td className="px-4 py-3.5">
                        <SeverityPill severity={bug.severity} />
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusPill status={bug.status} />
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 text-xs">
                        {formatDate(bug.createdAt)}
                      </td>
                      <td className="px-4 py-3.5">
                        <Link
                          href={`/bugs/${bug.id}`}
                          className="inline-flex items-center gap-1 text-blue-500 hover:text-blue-700 transition-colors text-xs font-medium"
                          title="View bug details"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })
      )}

      {/* ── FAB ──────────────────────────────────────────────────────── */}
      <Link
        href="/run-test"
        className="fixed bottom-8 right-8 h-14 w-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg flex items-center justify-center transition-all hover:scale-105"
        title="Run New Test"
      >
        <Plus className="h-6 w-6" />
      </Link>
    </div>
  );
}
