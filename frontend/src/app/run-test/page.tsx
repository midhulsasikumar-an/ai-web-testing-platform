"use client";

import { Play, Link as LinkIcon, Bot, X } from "lucide-react";
import { useState, useEffect, useMemo, useRef } from "react";
import AIChatPanel from "@/components/ai-chat-panel/AIChatPanel";
import { startTest, getTestById, TestApiResponse, AIPlanResponse } from "@/services/test-api";
import { useAuth } from "@/context/auth-context";
import { cn } from "@/lib/utils";

type FormErrors = {
  targetUrl?: string;
  testName?: string;
  goal?: string;
};

type RerunConfig = {
  targetUrl?: string;
  testName?: string;
  goal?: string;
  testType?: string;
  browser?: string;
  device?: string;
  coverageLevel?: string;
  executionSettings?: Record<string, unknown> | null;
  aiPlan?: AIPlanResponse | null;
};

const RERUN_CONFIG_KEY = "test_history_rerun_config";
const STORAGE_PENDING_RUN_TEST_KEY = "ai_workspace_pending_run_test";

function readLatestCopilotGoal(panelRoot: HTMLDivElement | null): string {
  if (!panelRoot) {
    return "";
  }

  const typedInput = panelRoot.querySelector("textarea") as HTMLTextAreaElement | null;
  const typedGoal = typedInput?.value?.trim() ?? "";
  if (typedGoal) {
    return typedGoal;
  }

  const userMessages = Array.from(panelRoot.querySelectorAll("div.bg-blue-600.text-white")) as HTMLElement[];
  const lastMessage = userMessages[userMessages.length - 1];
  return lastMessage?.textContent?.trim() ?? "";
}

function readScreenshotUrl(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const artifactUrl = record.artifact_url ?? record.path ?? record.url;
    if (typeof artifactUrl === "string") {
      return artifactUrl;
    }
  }

  return "";
}

type TimelineRow = {
  time: string;
  level: string;
  text: string;
  color: string;
  status?: string;
  count?: number;
};

function normalizeStatus(value?: string | null): string {
  const status = String(value ?? "").trim().toLowerCase();
  if (!status) return "idle";
  if (["running", "queued", "planning"].includes(status)) return status;
  if (["completed", "pass", "passed", "success"].includes(status)) return "completed";
  if (["completed_with_failures", "partial_success", "partial", "with_failures"].includes(status)) return "completed_with_failures";
  if (["warning", "failed", "fail", "timed_out", "timeout", "cancelled", "cancel_requested"].includes(status)) return status;
  return status;
}

function statusLabel(value?: string | null): string {
  const status = normalizeStatus(value);
  const map: Record<string, string> = {
    idle: "Idle",
    planning: "Planning",
    queued: "Queued",
    running: "Running",
    completed: "Completed",
    completed_with_failures: "Completed With Failures",
    pass: "Passed",
    passed: "Passed",
    success: "Passed",
    warning: "Warning",
    failed: "Failed",
    fail: "Failed",
    timed_out: "Timed Out",
    timeout: "Timed Out",
    cancelled: "Cancelled",
    cancel_requested: "Cancel Requested",
  };

  return map[status] ?? status.replace(/_/g, " ");
}

function statusTone(value?: string | null): string {
  const status = normalizeStatus(value);
  if (["running", "queued", "planning"].includes(status)) return "border-blue-200 bg-blue-50 text-blue-700";
  if (["completed", "pass", "passed", "success"].includes(status)) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (["completed_with_failures"].includes(status)) return "border-amber-200 bg-amber-50 text-amber-700";
  if (["warning", "timed_out", "timeout"].includes(status)) return "border-amber-200 bg-amber-50 text-amber-700";
  if (["failed", "fail", "cancelled", "cancel_requested"].includes(status)) return "border-red-200 bg-red-50 text-red-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function progressTone(value?: string | null): string {
  const status = normalizeStatus(value);
  if (["running", "queued", "planning"].includes(status)) return "bg-blue-500";
  if (["completed", "pass", "passed", "success"].includes(status)) return "bg-emerald-500";
  if (["warning", "timed_out", "timeout"].includes(status)) return "bg-amber-500";
  if (["failed", "fail", "cancelled", "cancel_requested"].includes(status)) return "bg-red-500";
  return "bg-slate-400";
}

function compressTimelineRows(rows: TimelineRow[]): TimelineRow[] {
  const output: TimelineRow[] = [];
  let successRun: TimelineRow[] = [];

  const flushSuccessRun = () => {
    if (successRun.length === 0) {
      return;
    }

    if (successRun.length === 1) {
      output.push(successRun[0]);
    } else {
      const first = successRun[0];
      const last = successRun[successRun.length - 1];
      output.push({
        ...first,
        text: `${successRun.length} successful steps collapsed: ${first.text}${last.text !== first.text ? ` ... ${last.text}` : ""}`,
        count: successRun.length,
      });
    }

    successRun = [];
  };

  rows.forEach((row) => {
    if ((row.status || row.level).toLowerCase() === "pass") {
      successRun.push(row);
      return;
    }

    flushSuccessRun();
    output.push(row);
  });

  flushSuccessRun();
  return output.slice(0, 120);
}

export default function RunTestPage() {
  const [targetUrl, setTargetUrl] = useState("");
  const [testName, setTestName] = useState("");
  const [testType, setTestType] = useState("e2e");
  const [aiPlan, setAiPlan] = useState<AIPlanResponse | null>(null);
  const [planSuppressed, setPlanSuppressed] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [initialInstruction, setInitialInstruction] = useState<string>("");
  useAuth();

  const [testId, setTestId] = useState<string | null>(null);
  const [testData, setTestData] = useState<TestApiResponse | null>(null);
  const [running, setRunning] = useState(false);
  useTestPolling(testId, setTestData, setRunning);
  const [browser, setBrowser] = useState("");
  const [device, setDevice] = useState("");
  const [coverageLevel, setCoverageLevel] = useState("");
  const [executionSettings, setExecutionSettings] = useState<Record<string, unknown> | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  const [planExpanded, setPlanExpanded] = useState(true);
  const aiPanelHostRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const [followTimeline, setFollowTimeline] = useState(true);

  useEffect(() => {
    console.log("RunTestPage: effect mounted");
    if (typeof window === "undefined") {
      return;
    }

    const loadHandoffPayload = () => {
      const handoffRaw = window.localStorage.getItem(STORAGE_PENDING_RUN_TEST_KEY);
      if (handoffRaw) {
        try {
          const payload = JSON.parse(handoffRaw);
          const now = new Date().getTime();
          const createdTime = new Date(payload.created_at).getTime();
          
          console.log("Received payload", payload);
          
          // Ignore payloads older than 10 minutes
          if (!isNaN(createdTime) && (now - createdTime) < 10 * 60 * 1000) {
            if (payload.url) setTargetUrl(payload.url);
            if (payload.instruction) {
              console.log("Handoff instruction populated:", payload.instruction);
              console.log("Handoff instruction length:", payload.instruction?.length);
              setInitialInstruction(payload.instruction);
            } else {
              console.warn("Handoff payload missing instruction field");
            }
          } else {
            console.warn("Ignoring stale handoff payload");
          }
        } catch (error) {
          console.error("Failed to parse handoff payload", error);
        } finally {
          // Delay removal to allow React Strict Mode's double-invocation to complete safely
          setTimeout(() => {
            console.log("Removing handoff payload from localStorage");
            window.localStorage.removeItem(STORAGE_PENDING_RUN_TEST_KEY);
          }, 500);
        }
      }
    };

    const loadRerunConfig = () => {
      const raw = window.localStorage.getItem(RERUN_CONFIG_KEY);
      if (!raw) {
        return;
      }

      try {
        const config = JSON.parse(raw) as RerunConfig;
        if (config.targetUrl) setTargetUrl(config.targetUrl);
        if (config.testName) setTestName(config.testName);
        if (config.testType) setTestType(config.testType);
        if (config.browser) setBrowser(config.browser);
        if (config.device) setDevice(config.device);
        if (config.coverageLevel) setCoverageLevel(config.coverageLevel);
        setExecutionSettings(config.executionSettings ?? null);
        if (config.aiPlan) setAiPlan(config.aiPlan);
        if (config.goal) {
          setInitialInstruction(config.goal);
          setPlanSuppressed(false);
          setTestData((current) => current);
        }
      } catch (error) {
        console.error("Failed to restore rerun configuration", error);
      } finally {
        window.localStorage.removeItem(RERUN_CONFIG_KEY);
      }
    };

    loadHandoffPayload();
    loadRerunConfig();

    return () => {
      console.log("RunTestPage: effect cleanup");
    };
  }, []);

  const results = (testData?.results ?? []) as Array<Record<string, unknown>>;
  const streamLogs = testData?.stream_logs ?? [];

  const executionStatus = normalizeStatus(testData?.status ?? (running ? "running" : "idle"));
  const terminalLogs = streamLogs.length > 0
    ? compressTimelineRows(streamLogs.map((entry) => ({
        time: entry.time,
        level: entry.level.toUpperCase(),
        text: entry.msg,
        color: entry.level === 'error' ? 'text-red-400' : entry.level === 'warn' ? 'text-amber-400' : 'text-blue-400',
        status: entry.level,
      })))
    : compressTimelineRows(results.map((r) => ({
      time: (r['time'] as string) ?? new Date().toLocaleTimeString('en-GB', { hour12: false }),
      level: ((r['status'] as string) ?? 'INFO').toUpperCase(),
      text: r['test'] ? `${String(r['test'])}: ${String(r['details'] ?? JSON.stringify(r))}` : JSON.stringify(r),
      color: (r['status'] === 'fail') ? 'text-red-400' : 'text-blue-400',
      status: String(r['status'] ?? ''),
    })));

  const activePlan = planSuppressed ? aiPlan : aiPlan ?? testData?.ai_plan ?? null;

  const handlePlanGenerated = (plan: AIPlanResponse) => {
    setPlanSuppressed(false);
    setAiPlan(plan);
  };

  const handleClearPlan = () => {
    setPlanSuppressed(true);
    setAiPlan(null);
  };

  const runTest = async () => {
    const nextErrors: FormErrors = {};
    const normalizedUrl = targetUrl.trim();
    const normalizedTestName = testName.trim();
    const goal = readLatestCopilotGoal(aiPanelHostRef.current);

    if (!normalizedUrl) {
      nextErrors.targetUrl = "Target URL is required.";
    }

    if (!normalizedTestName) {
      nextErrors.testName = "Test Name is required.";
    }

    if (!goal) {
      nextErrors.goal = "Add the test goal in AI Copilot first.";
    }

    setFormErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    try {
      setRunning(true);
      setFormErrors({});
      setTestData(null);
      setTestId(null);
      setPlanSuppressed(false);
      const res = await startTest({
        url: normalizedUrl,
        testName: normalizedTestName,
        goal,
        testType,
        aiPlan: activePlan,
        browser: browser || undefined,
        device: device || undefined,
        coverageLevel: coverageLevel || undefined,
        executionSettings: executionSettings ?? undefined,
      });
      setTestId(res.test_id);
    } catch (error) {
      console.error('Failed to start test', error);
      setRunning(false);
      setFormErrors((current) => ({
        ...current,
        goal: error instanceof Error ? error.message : 'Failed to start the test.',
      }));
    }
  };

  useEffect(() => {
    if (running && followTimeline && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [followTimeline, running, terminalLogs]);

  const terminalSummary = useMemo(() => {
    if (!Array.isArray(streamLogs) || streamLogs.length === 0) {
      return null;
    }
    for (let i = streamLogs.length - 1; i >= 0; i -= 1) {
      const entry = streamLogs[i] as Record<string, unknown>;
      if (entry && entry.type === "terminal_summary") {
        return {
          time: String(entry.time || ""),
          level: String(entry.level || "info").toLowerCase(),
          text: String(entry.msg || entry.message || ""),
        };
      }
    }
    return null;
  }, [streamLogs]);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-4">
      <div className="grid h-full min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-h-0 flex-col gap-3.5">
          {terminalSummary ? (
            <section
              data-testid="execution-summary-banner"
              className={cn(
                "overflow-hidden rounded-xl border shadow-xs-token",
                terminalSummary.level === "error"
                  ? "border-red-200 bg-gradient-to-br from-red-50 via-white to-white"
                  : terminalSummary.level === "warn"
                    ? "border-amber-200 bg-gradient-to-br from-amber-50 via-white to-white"
                    : "border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-white"
              )}
            >
              <div className="px-4 py-3.5">
                <pre className="whitespace-pre-wrap break-words font-mono text-[12.5px] leading-relaxed text-slate-800">{terminalSummary.text}</pre>
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs-token">
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_auto] lg:items-end">
              <div className="space-y-1">
                <label className="block text-eyebrow">Target URL</label>
                <div className="relative">
                  <LinkIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="url"
                    value={targetUrl}
                    onChange={(event) => setTargetUrl(event.target.value)}
                    className={`h-9 w-full rounded-lg border bg-slate-50 py-1.5 pl-9 pr-3 text-[13px] text-slate-900 outline-none transition-colors focus:bg-white ${formErrors.targetUrl ? 'border-red-300 focus:border-red-500' : 'border-slate-200 focus:border-blue-500'}`}
                    placeholder="Enter target URL"
                  />
                </div>
                {formErrors.targetUrl ? <p className="text-[11px] text-red-600">{formErrors.targetUrl}</p> : null}
              </div>

              <div className="space-y-1">
                <label className="block text-eyebrow">Test Name</label>
                <input
                  type="text"
                  value={testName}
                  onChange={(event) => setTestName(event.target.value)}
                  className={`h-9 w-full rounded-lg border bg-slate-50 px-3 py-1.5 text-[13px] text-slate-900 outline-none transition-colors focus:bg-white ${formErrors.testName ? 'border-red-300 focus:border-red-500' : 'border-slate-200 focus:border-blue-500'}`}
                  placeholder="Enter test name..."
                />
                {formErrors.testName ? <p className="text-[11px] text-red-600">{formErrors.testName}</p> : null}
              </div>

              <input type="hidden" value={testType} readOnly />

              <div className="flex flex-col gap-1">
                <button onClick={runTest} disabled={running} className="h-9 whitespace-nowrap rounded-lg bg-slate-900 px-4 text-[13px] font-medium text-white shadow-xs-token transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
                  <span className="flex items-center justify-center gap-1.5">
                    <Play className="h-3.5 w-3.5" />
                    {running ? 'Running...' : 'Run Test'}
                  </span>
                </button>
                {formErrors.goal ? <p className="max-w-xs text-[11px] text-red-600">{formErrors.goal}</p> : null}
              </div>
            </div>
          </section>

          <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <div className="min-w-0">
                <h2 className="text-h3">Generated Test Plan</h2>
                <p className="text-muted-sm">Scenario name, description, and steps only.</p>
              </div>
              <button
                type="button"
                onClick={() => setPlanExpanded((current) => !current)}
                className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                {planExpanded ? 'Collapse' : 'Expand'}
              </button>
            </div>

            {planExpanded ? (
              <div className="flex-1 overflow-y-auto p-4">
                {activePlan ? (
                  <div className="space-y-3">
                    <div className="space-y-1.5 rounded-lg border border-slate-200 bg-slate-50/60 p-3.5">
                      <p className="text-eyebrow">Scenario name</p>
                      <p className="text-[13.5px] font-semibold text-slate-900">{activePlan.test_case?.title || 'Untitled scenario'}</p>
                      <p className="text-[12.5px] leading-relaxed text-slate-600">{activePlan.summary || 'No plan summary available.'}</p>
                    </div>

                    <div className="space-y-2">
                      {Array.isArray(activePlan.test_case?.steps) ? activePlan.test_case.steps.map((step, index) => (
                        <div key={`${step.action}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs-token">
                          <p className="text-[13px] font-semibold text-slate-900">Step {index + 1}: {step.action}</p>
                          <p className="mt-1 break-words text-[12.5px] text-slate-600">{step.target || step.selector || step.value || 'No step details provided.'}</p>
                        </div>
                      )) : (
                        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3.5 text-[12.5px] text-slate-500">Generate a plan to see scenario steps.</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-5 text-[12.5px] text-slate-500">
                    Use the AI assistant to generate a plan first.
                  </div>
                )}
              </div>
            ) : null}
          </section>

          <section className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <div className="min-w-0">
                <h2 className="text-h3">Execution Terminal</h2>
                <p className="text-muted-sm">Live terminal-style logs from the current run.</p>
              </div>
              <div className={cn("rounded-full border px-2.5 py-1 text-[11px] font-medium", statusTone(executionStatus))}>
                {statusLabel(executionStatus)}
              </div>
            </div>

            <div
              ref={terminalRef}
              onScroll={() => {
                const node = terminalRef.current;
                if (!node) {
                  return;
                }

                const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
                setFollowTimeline(distanceFromBottom < 48);
              }}
              className="h-[24rem] overflow-y-auto bg-slate-950 px-4 py-3 font-mono text-[12.5px] text-slate-100"
            >
              <div className="space-y-1.5">
                {terminalLogs.length > 0 ? terminalLogs.map((log, index) => (
                  <div key={`${log.time}-${index}`} className="flex gap-2.5 rounded-md border border-slate-800/80 bg-slate-950/80 px-2.5 py-1.5 shadow-inner-token">
                    <span className="shrink-0 text-slate-400">[{log.time}]</span>
                    <span className={`${log.color} w-16 shrink-0 font-bold`}>{log.level}</span>
                    <span className="break-words whitespace-pre-wrap text-slate-200">{log.text}</span>
                  </div>
                )) : (
                  <div className="rounded-md border border-dashed border-slate-800/80 bg-slate-950/80 px-3 py-3 text-slate-400">
                    No execution logs yet. Start a test to see live output.
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>

        <div ref={aiPanelHostRef} className="hidden min-h-0 lg:flex lg:h-full lg:w-[380px] lg:shrink-0">
          <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
            <AIChatPanel
              open={true}
              setOpen={() => undefined}
              targetUrl={targetUrl}
              testType={testType}
              testData={testData}
              currentPlan={activePlan}
              onPlanGenerated={handlePlanGenerated}
              onClearPlan={handleClearPlan}
              executionStatus={executionStatus}
              initialInput={initialInstruction}
            />
          </div>
        </div>
      </div>

      <div className="fixed bottom-6 right-6 z-30 flex flex-col items-end gap-3 lg:hidden">
        {!aiPanelOpen ? (
          <button
            type="button"
            onClick={() => setAiPanelOpen(true)}
            className="inline-flex h-11 items-center gap-2 rounded-full bg-slate-900 px-4 text-[13px] font-semibold text-white shadow-lg-token transition-colors hover:bg-slate-800"
            aria-label="Open AI assistant"
          >
            <Bot className="h-4 w-4" />
            AI Assistant
          </button>
        ) : null}

        {aiPanelOpen ? (
          <div className="fixed inset-0 z-40 flex flex-col bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <p className="text-h3">AI Assistant</p>
              <button
                type="button"
                onClick={() => setAiPanelOpen(false)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-700 transition-colors hover:bg-slate-50"
                aria-label="Close AI assistant"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="flex-1 min-h-0">
              <AIChatPanel
                open={true}
                setOpen={() => undefined}
                targetUrl={targetUrl}
                testType={testType}
                testData={testData}
                currentPlan={activePlan}
                onPlanGenerated={handlePlanGenerated}
                onClearPlan={handleClearPlan}
                executionStatus={executionStatus}
                initialInput={initialInstruction}
              />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// Side effects: polling test status when a test is started
function useTestPolling(testId: string | null, setTestData: (d: TestApiResponse | null)=>void, setRunning: (v:boolean)=>void) {
  useEffect(() => {
    if (!testId) return;

    let mounted = true;
    const interval = window.setInterval(async () => {
      try {
        const data = await getTestById(testId);
        if (!mounted) return;
        setTestData(data as TestApiResponse);
        if ((data as TestApiResponse)['status'] && (data as TestApiResponse)['status'] !== 'running') {
          setRunning(false);
          window.clearInterval(interval);
        }
      } catch (e) {
        console.error('Polling failed', e);
      }
    }, 2000);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [testId, setTestData, setRunning]);
}
