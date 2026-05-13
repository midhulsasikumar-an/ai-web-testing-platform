"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2, Play, Zap, Globe, GitBranch,
  RefreshCw, ScanLine, Accessibility, Folder,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface TestConfigFormProps {
  url: string;
  onUrlChange: (value: string) => void;
  githubUrl: string;
  onGithubUrlChange: (value: string) => void;
  projectName: string;
  onProjectNameChange: (value: string) => void;
  testType: "full" | "ai" | "accessibility";
  onTestTypeChange: (value: "full" | "ai" | "accessibility") => void;
  loading: boolean;
  onRunTest: () => void;
}

// ── Test type options ──────────────────────────────────────────────

const testTypes = [
  { id: "full" as const, label: "Full Regression", icon: RefreshCw },
  { id: "ai" as const, label: "AI Scan", icon: ScanLine },
  { id: "accessibility" as const, label: "Accessibility", icon: Accessibility },
];

// ── Component ──────────────────────────────────────────────────────

export function TestConfigForm({
  url,
  onUrlChange,
  githubUrl,
  onGithubUrlChange,
  projectName,
  onProjectNameChange,
  testType,
  onTestTypeChange,
  loading,
  onRunTest,
}: TestConfigFormProps) {
  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-4 border-b border-border/50 bg-muted/20">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-lg">New Intelligence Probe</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              Deploy AI agents to crawl and identify regressions.
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" /> Target URL
            </label>
            <Input
              placeholder="https://app.example.com"
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onRunTest()}
              disabled={loading}
              className="h-10 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <GitBranch className="h-3.5 w-3.5" /> GitHub Repo (optional)
            </label>
            <Input
              placeholder="https://github.com/org/repo"
              value={githubUrl}
              onChange={(e) => onGithubUrlChange(e.target.value)}
              disabled={loading}
              className="h-10 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Folder className="h-3.5 w-3.5" /> Project Name
            </label>
            <Input
              placeholder="My AI Testing Project"
              value={projectName}
              onChange={(e) => onProjectNameChange(e.target.value)}
              disabled={loading}
              className="h-10 text-sm"
            />
          </div>
        </div>

        {/* Test type toggles */}
        <div className="space-y-2 pt-2 border-t border-border/50">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block mb-2">
            Analysis Mode
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {testTypes.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => onTestTypeChange(id)}
                disabled={loading}
                className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 ${
                  testType === id
                    ? "bg-primary text-primary-foreground border-primary shadow-sm ring-1 ring-primary/20"
                    : "bg-background text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        <Button 
          onClick={onRunTest} 
          disabled={loading || !url.trim()} 
          size="lg" 
          className="w-full h-11 text-sm font-bold tracking-wide mt-4"
        >
          {loading ? (
            <><Loader2 className="h-4 w-4 animate-spin mr-2" />Deploying Probe...</>
          ) : (
            <><Play className="h-4 w-4 mr-2" />Initialize Test Run</>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
