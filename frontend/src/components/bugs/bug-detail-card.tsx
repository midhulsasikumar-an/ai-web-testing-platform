"use client";

import type { Bug } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { AvatarCircle } from "@/components/shared/avatar-circle";
import { MetadataField } from "@/components/shared/metadata-field";
import { TerminalLog } from "@/components/shared/terminal-log";
import { formatDate, formatTime24 } from "@/lib/formatters";
import { ThreadPanel } from "@/components/collaboration/thread-panel";
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
                <SeverityBadge severity={bug.severity} />
                <StatusBadge status={bug.status} />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                <span>{formatDate(bug.createdAt)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Link2 className="h-3.5 w-3.5" />
                <a href={bug.url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1 text-primary">
                  {bug.url}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold mb-2">Description</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{bug.description}</p>
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
                  <span className="text-muted-foreground leading-relaxed pt-0.5">{step}</span>
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
              <TerminalLog
                entries={bug.logs.map((entry) => ({
                  time: formatTime24(entry.timestamp),
                  level: entry.level,
                  msg: entry.message,
                }))}
              />
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
            <MetadataField icon={User} label="Assigned To">
              {bug.assignedTo ? (
                <div className="flex items-center gap-2">
                  <AvatarCircle name={bug.assignedTo} size="md" />
                  <span className="text-sm font-medium">{bug.assignedTo}</span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Unassigned</span>
              )}
            </MetadataField>

            <MetadataField icon={Tag} label="Priority">
              <SeverityBadge severity={bug.severity} />
            </MetadataField>

            <MetadataField icon={Clock} label="Status">
              <StatusBadge status={bug.status} />
            </MetadataField>

            <MetadataField icon={Calendar} label="Created">
              <p className="text-sm">{formatDate(bug.createdAt)}</p>
            </MetadataField>

            {bug.environment && (
              <MetadataField icon={Monitor} label="Environment">
                <p className="text-sm text-muted-foreground">{bug.environment}</p>
              </MetadataField>
            )}

            <MetadataField icon={Link2} label="URL">
              <a href={bug.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline flex items-center gap-1 break-all">
                {bug.url}
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </MetadataField>
          </CardContent>
        </Card>

        {/* Collaboration Thread Panel */}
        <ThreadPanel objectType="bug" objectId={bug.id} title={`Discussion for ${bug.title}`} />
      </div>
    </div>
  );
}
