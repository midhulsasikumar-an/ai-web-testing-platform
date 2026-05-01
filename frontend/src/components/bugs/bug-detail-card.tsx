"use client";

import { Bug } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { severityColor, statusColor, formatDate } from "./bug-utils";
import {
  ExternalLink, Calendar, AlertTriangle, Link2,
  Terminal, Monitor, User, Tag, Clock,
} from "lucide-react";

interface BugDetailCardProps {
  bug: Bug;
}

export function BugDetailCard({ bug }: BugDetailCardProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Main Content — Left 2 cols */}
      <div className="lg:col-span-2 space-y-6">
        {/* Header info */}
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <p className="text-xs font-mono text-primary font-medium">{bug.id}</p>
                <CardTitle className="text-xl">{bug.title}</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={severityColor(bug.severity)}>
                  {bug.severity}
                </Badge>
                <Badge variant="secondary" className={statusColor(bug.status)}>
                  {bug.status}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Meta row */}
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                <span>{formatDate(bug.createdAt)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Link2 className="h-3.5 w-3.5" />
                <a
                  href={bug.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline flex items-center gap-1 text-primary"
                >
                  {bug.url}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>

            {/* Description */}
            <div>
              <h3 className="text-sm font-semibold mb-2">Description</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {bug.description}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Reproduction Steps */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Reproduction Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {bug.steps.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                    {i + 1}
                  </span>
                  <span className="text-muted-foreground leading-relaxed pt-0.5">
                    {step}
                  </span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        {/* System Logs */}
        {bug.logs && bug.logs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" />
                System Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg bg-[#0d1117] p-4 max-h-64 overflow-y-auto terminal-log">
                {bug.logs.map((entry, i) => {
                  const levelColors: Record<string, string> = {
                    info: "log-info",
                    warn: "log-warn",
                    error: "log-error",
                    success: "log-success",
                  };
                  const levelIcons: Record<string, string> = {
                    info: "ℹ",
                    warn: "⚠",
                    error: "✕",
                    success: "✓",
                  };
                  const time = new Date(entry.timestamp).toLocaleTimeString("en-US", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  });
                  return (
                    <div key={i} className="flex gap-2 py-0.5 leading-relaxed">
                      <span className="log-timestamp shrink-0 select-none">[{time}]</span>
                      <span className={`shrink-0 w-3 text-center select-none ${levelColors[entry.level]}`}>
                        {levelIcons[entry.level]}
                      </span>
                      <span className={levelColors[entry.level]}>{entry.message}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Screenshot Evidence */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Monitor className="h-4 w-4 text-primary" />
              Screenshot Evidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 flex flex-col items-center justify-center gap-3 text-center">
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Monitor className="h-6 w-6 text-primary/60" />
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Screenshots are captured during automated test runs
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  Tap the &quot;Re-run Test&quot; button to capture fresh screenshots
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Sidebar — Metadata */}
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Bug Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Assigned To */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                <User className="h-3 w-3" /> Assigned To
              </div>
              {bug.assignedTo ? (
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-[0.55rem] font-bold">
                    {bug.assignedTo.split(" ").map(n => n[0]).join("")}
                  </div>
                  <span className="text-sm font-medium">{bug.assignedTo}</span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Unassigned</span>
              )}
            </div>

            {/* Priority */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                <Tag className="h-3 w-3" /> Priority
              </div>
              <Badge variant="outline" className={severityColor(bug.severity)}>
                {bug.severity}
              </Badge>
            </div>

            {/* Status */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                <Clock className="h-3 w-3" /> Status
              </div>
              <Badge variant="secondary" className={statusColor(bug.status)}>
                {bug.status}
              </Badge>
            </div>

            {/* Created */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                <Calendar className="h-3 w-3" /> Created
              </div>
              <p className="text-sm">{formatDate(bug.createdAt)}</p>
            </div>

            {/* Environment */}
            {bug.environment && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <Monitor className="h-3 w-3" /> Environment
                </div>
                <p className="text-sm text-muted-foreground">{bug.environment}</p>
              </div>
            )}

            {/* URL */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                <Link2 className="h-3 w-3" /> URL
              </div>
              <a
                href={bug.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline flex items-center gap-1 break-all"
              >
                {bug.url}
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
