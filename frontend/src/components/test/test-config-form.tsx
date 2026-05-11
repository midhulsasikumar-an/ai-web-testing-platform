"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Loader2, Play, Zap, Globe, GitBranch,
  RefreshCw, ScanLine, Accessibility,
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
    <>
      {/* Probe header */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shrink-0">
              <Zap className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Automated Intelligence Probe</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Deploy AI agents to crawl, interact, and identify regressions across your environment.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Input fields */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" /> Target URL
            </label>
            <Input
              placeholder="https://app.example.com"
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onRunTest()}
              disabled={loading}
              className="h-11"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <GitBranch className="h-3.5 w-3.5" /> GitHub Repo (optional)
            </label>
            <Input
              placeholder="https://github.com/org/repo"
              value={githubUrl}
              onChange={(e) => onGithubUrlChange(e.target.value)}
              disabled={loading}
              className="h-11"
            />
          </div>
                    <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Project Name
            </label>

            <Input
              placeholder="My AI Testing Project"
              value={projectName}
              onChange={(e) => onProjectNameChange(e.target.value)}
              disabled={loading}
              className="h-11"
            />
          </div>

          {/* Test type toggles */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Test Type
            </label>
            <div className="flex flex-wrap gap-2">
              {testTypes.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => onTestTypeChange(id)}
                  disabled={loading}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-200 ${
                    testType === id
                      ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20"
                      : "bg-card text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          <Button onClick={onRunTest} disabled={loading || !url.trim()} size="lg" className="w-full mt-2 h-12 text-base font-semibold">
            {loading ? (
              <><Loader2 className="h-5 w-5 animate-spin mr-2" />Scanning...</>
            ) : (
              <><Play className="h-5 w-5 mr-2" />Run Test</>
            )}
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
