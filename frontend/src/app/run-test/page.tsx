"use client";

import { Play, Link as LinkIcon, Bot, X, FilePlus2, Save, Sparkles, Lock } from "lucide-react";
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import AIChatPanel from "@/components/ai-chat-panel/AIChatPanel";
import { startTest, getTestById, getTestStream, streamTestEvents, TestApiResponse, AIPlanResponse } from "@/services/test-api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRunWorkspace, clearRunTestStorage } from "@/lib/run-test-store";

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

type GeneratedPlanStep = AIPlanResponse["test_case"]["steps"][number];
type GeneratedPlanCase = AIPlanResponse["test_case"];
type GeneratedExecutionPlan = AIPlanResponse & {
  steps?: GeneratedPlanStep[];
  scenario_cases?: GeneratedPlanCase[];
  scenarios?: GeneratedPlanCase[];
  plan_metrics?: {
    generated_steps?: number;
  } | null;
};
type GeneratedPlanForValidation = GeneratedExecutionPlan & {
  steps: GeneratedPlanStep[];
};

const RERUN_CONFIG_KEY = "test_history_rerun_config";
const STORAGE_PENDING_RUN_TEST_KEY = "ai_workspace_pending_run_test";
const RUN_TEST_INPUT_REQUIRED_MESSAGE =
  "Please provide a test goal or generate a test plan using AI Copilot before running the test.";

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

function compressTimelineRows(rows: TimelineRow[]): TimelineRow[] {
  const output: TimelineRow[] = [];
  let successRun: TimelineRow[] = [];

  const flushSuccessRun = () => {
    if (successRun.length === 0) return;
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
  return output.slice(0, 160);
}

function readLatestCopilotText(aiPanelHost: HTMLDivElement | null): string {
  if (!aiPanelHost) return "";
  const typedInput = aiPanelHost.querySelector("textarea") as HTMLTextAreaElement | null;
  return typedInput?.value?.trim() ?? "";
}

function getPlanCases(plan?: GeneratedExecutionPlan | null): GeneratedPlanCase[] {
  if (!plan) return [];
  const cases: GeneratedPlanCase[] = [];
  const primaryCase = plan.test_case as GeneratedPlanCase | null | undefined;
  if (primaryCase) cases.push(primaryCase);
  if (Array.isArray(plan.test_cases)) {
    cases.push(...plan.test_cases.filter(Boolean));
  }
  if (Array.isArray(plan.scenario_cases)) {
    cases.push(...plan.scenario_cases.filter(Boolean));
  }
  if (Array.isArray(plan.scenarios)) {
    cases.push(...plan.scenarios.filter(Boolean));
  }
  return cases;
}

function hasExecutablePlanStep(step: GeneratedPlanStep | null | undefined): boolean {
  if (!step) return false;
  return Boolean(
    String(step.action ?? "").trim() ||
      String(step.target ?? "").trim() ||
      String(step.selector ?? "").trim() ||
      String(step.value ?? "").trim()
  );
}

function getGeneratedPlanSteps(plan?: GeneratedExecutionPlan | null): GeneratedPlanStep[] {
  if (!plan) return [];
  const directSteps = Array.isArray(plan.steps) ? plan.steps : [];
  const caseSteps = getPlanCases(plan).flatMap((testCase) => {
    const steps = Array.isArray(testCase.steps) ? testCase.steps : [];
    return steps;
  });
  return [...directSteps, ...caseSteps].filter(hasExecutablePlanStep);
}

function getGeneratedPlanStepCount(plan?: GeneratedExecutionPlan | null): number {
  return getGeneratedPlanSteps(plan).length;
}

function getGeneratedPlanForValidation(plan?: GeneratedExecutionPlan | null): GeneratedPlanForValidation | null {
  if (!plan) return null;
  const steps = getGeneratedPlanSteps(plan);
  if (steps.length === 0) return null;
  return { ...plan, steps };
}

export default function RunTestPage() {
  const workspace = useRunWorkspace();
  const {
    state,
    update,
    reset,
    setChatInput,
    appendChat,
    resetChat,
    setExecutionStatusMessage,
    hydrated,
  } = workspace;

  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [terminalCollapsed, setTerminalCollapsed] = useState(false);
  const aiPanelHostRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const [generating] = useState(false);
  void generating;

  useEffect(() => {
    if (typeof window === "undefined") return;

    const loadHandoffPayload = () => {
      const handoffRaw = window.localStorage.getItem(STORAGE_PENDING_RUN_TEST_KEY);
      if (!handoffRaw) return;
      try {
        const payload = JSON.parse(handoffRaw) as { created_at?: string; url?: string; instruction?: string };
        const now = new Date().getTime();
        const createdTime = payload.created_at ? new Date(payload.created_at).getTime() : 0;
        if (!Number.isNaN(createdTime) && createdTime > 0 && now - createdTime < 10 * 60 * 1000) {
          update((prev) => ({
            ...prev,
            targetUrl: payload.url ?? prev.targetUrl,
            initialInstruction: payload.instruction ?? prev.initialInstruction,
            chatInput: payload.instruction ?? prev.chatInput,
            lastInstruction: payload.instruction ?? prev.lastInstruction,
          }));
        }
      } catch {
        // ignore
      } finally {
        window.setTimeout(() => {
          window.localStorage.removeItem(STORAGE_PENDING_RUN_TEST_KEY);
        }, 500);
      }
    };

    const loadRerunConfig = () => {
      const raw = window.localStorage.getItem(RERUN_CONFIG_KEY);
      if (!raw) return;
      try {
        const config = JSON.parse(raw) as RerunConfig;
        update((prev) => ({
          ...prev,
          targetUrl: config.targetUrl ?? prev.targetUrl,
          testName: config.testName ?? prev.testName,
          testType: config.testType ?? prev.testType,
          browser: config.browser ?? prev.browser,
          device: config.device ?? prev.device,
          coverageLevel: config.coverageLevel ?? prev.coverageLevel,
          executionSettings: config.executionSettings ?? prev.executionSettings,
          aiPlan: config.aiPlan ?? prev.aiPlan,
          planSuppressed: false,
          initialInstruction: config.goal ?? prev.initialInstruction,
          chatInput: config.goal ?? prev.chatInput,
          lastInstruction: config.goal ?? prev.lastInstruction,
        }));
      } catch {
        // ignore
      } finally {
        window.localStorage.removeItem(RERUN_CONFIG_KEY);
      }
    };

    loadHandoffPayload();
    loadRerunConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useTestPolling(
    state.testId,
    hydrated,
    (next) => update((prev) => ({
      testData: typeof next === "function" ? next(prev.testData) : next,
    })),
    (running) => update({ running })
  );

  const streamLogs = useMemo(
    () => ((state.testData?.stream_logs ?? []) as Array<{ time: string; level: string; msg: string; type?: string; details?: Record<string, unknown> }>),
    [state.testData?.stream_logs]
  );
  const results = useMemo(
    () => ((state.testData?.results ?? []) as Array<Record<string, unknown>>),
    [state.testData?.results]
  );

  const executionStatus = normalizeStatus(
    state.testData?.status ?? (state.running ? "running" : "idle")
  );

  const terminalLogs = useMemo(() => {
    if (streamLogs.length > 0) {
      return compressTimelineRows(
        streamLogs.map((entry) => ({
          time: entry.time,
          level: entry.level.toUpperCase(),
          text: entry.msg,
          color:
            entry.level === "error"
              ? "text-red-400"
              : entry.level === "warn"
                ? "text-amber-400"
                : "text-blue-400",
          status: entry.level,
        }))
      );
    }
    return compressTimelineRows(
      results.map((r) => ({
        time: (r.time as string) ?? new Date().toLocaleTimeString("en-GB", { hour12: false }),
        level: ((r.status as string) ?? "INFO").toUpperCase(),
        text: r.test
          ? `${String(r.test)}: ${String(r.details ?? JSON.stringify(r))}`
          : JSON.stringify(r),
        color: r.status === "fail" ? "text-red-400" : "text-blue-400",
        status: String(r.status ?? ""),
      }))
    );
  }, [streamLogs, results]);

  const activePlan = state.aiPlan ?? state.testData?.ai_plan ?? null;

  const handlePlanGenerated = useCallback(
    (plan: AIPlanResponse) => {
      update({ planSuppressed: false, aiPlan: plan });
    },
    [update]
  );

  const handleClearPlan = useCallback(() => {
    update({ planSuppressed: true, aiPlan: null });
  }, [update]);

  const runTest = async () => {
    const nextErrors: FormErrors = {};
    const normalizedUrl = state.targetUrl.trim();
    const normalizedTestName = state.testName.trim();
    const testGoal = (state.chatInput.trim() || readLatestCopilotText(aiPanelHostRef.current)).trim();
    const executionPlan = activePlan as GeneratedExecutionPlan | null;
    const generatedPlan = getGeneratedPlanForValidation(executionPlan);
    const generatedStepsCount =
      generatedPlan?.steps.length ?? Number(executionPlan?.plan_metrics?.generated_steps ?? 0);
    const workspaceRestored = persisted;
    const hasInstruction = Boolean(testGoal?.trim());
    const hasGeneratedPlan = Boolean(
      generatedPlan &&
        Array.isArray(generatedPlan.steps) &&
        generatedPlan.steps.length > 0
    );
    const canRun = hasInstruction || hasGeneratedPlan;

    console.log("RUN TEST DEBUG", {
      testGoal,
      activePlan,
      executionPlan,
      generatedPlan,
      generatedStepsCount,
      workspaceRestored,
      canRun,
      planSuppressed: state.planSuppressed,
      stateAiPlan: state.aiPlan,
      testDataAiPlan: state.testData?.ai_plan,
    });

    if (!normalizedUrl) nextErrors.targetUrl = "Target URL is required.";
    if (!normalizedTestName) nextErrors.testName = "Test Name is required.";
    if (!canRun) {
      nextErrors.goal = RUN_TEST_INPUT_REQUIRED_MESSAGE;
    }

    setFormErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    try {
      update({ running: true, testData: null, testId: null, planSuppressed: false });
      setFormErrors({});
      const res = await startTest({
        url: normalizedUrl,
        testName: normalizedTestName,
        goal: testGoal,
        testType: state.testType,
        aiPlan: hasGeneratedPlan ? executionPlan : null,
        browser: state.browser || undefined,
        device: state.device || undefined,
        coverageLevel: state.coverageLevel || undefined,
        executionSettings: state.executionSettings ?? undefined,
      });
      update({ testId: res.test_id });
    } catch (error) {
      update({ running: false });
      setFormErrors((current) => ({
        ...current,
        goal: error instanceof Error ? error.message : "Failed to start the test.",
      }));
    }
  };

  const handleNewTest = useCallback(() => {
    if (typeof window !== "undefined") {
      const confirmed = window.confirm("Reset the workspace and clear the current execution?");
      if (!confirmed) return;
    }
    clearRunTestStorage();
    reset();
    setFormErrors({});
    setTerminalCollapsed(false);
  }, [reset]);

  useEffect(() => {
    if (state.followTimeline && state.running && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalLogs, state.followTimeline, state.running]);

  const terminalSummary = useMemo(() => {
    if (!Array.isArray(streamLogs) || streamLogs.length === 0) return null;
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

  const persisted = Boolean(state.testId || state.testData || state.aiPlan || state.chatMessages.length > 0);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-3 overflow-hidden">
      <div className="grid h-full min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto pr-0.5">
          <RunTestForm
            targetUrl={state.targetUrl}
            testName={state.testName}
            formErrors={formErrors}
            running={state.running}
            status={executionStatus}
            persisted={persisted}
            onTargetUrlChange={(value) => update({ targetUrl: value })}
            onTestNameChange={(value) => update({ testName: value })}
            onRun={runTest}
            onNewTest={handleNewTest}
          />

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
                <pre className="whitespace-pre-wrap break-words font-mono text-[12.5px] leading-relaxed text-slate-800">
                  {terminalSummary.text}
                </pre>
              </div>
            </section>
          ) : null}

          <TestPlanPanel
            plan={activePlan}
            expanded={state.planExpanded}
            onToggleExpanded={() => update({ planExpanded: !state.planExpanded })}
          />

          <ExecutionTerminal
            terminalRef={terminalRef}
            logs={terminalLogs}
            collapsed={terminalCollapsed}
            onToggleCollapsed={() => setTerminalCollapsed((v) => !v)}
            follow={state.followTimeline}
            onToggleFollow={() => update({ followTimeline: !state.followTimeline })}
            onScroll={() => {
              const node = terminalRef.current;
              if (!node) return;
              const distance = node.scrollHeight - node.scrollTop - node.clientHeight;
              update({ followTimeline: distance < 48 });
            }}
            status={executionStatus}
          />
        </div>

        <aside
          ref={aiPanelHostRef}
          className="hidden h-full min-h-0 lg:flex lg:flex-col lg:self-stretch lg:overflow-hidden"
        >
          <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
            <AIChatPanel
              open
              targetUrl={state.targetUrl}
              testType={state.testType}
              testData={state.testData}
              currentPlan={activePlan}
              onPlanGenerated={handlePlanGenerated}
              onClearPlan={handleClearPlan}
              onAppendMessage={appendChat}
              onResetChat={resetChat}
              onInstructionUsed={(instruction) => update({ lastInstruction: instruction })}
              onExecutionStatusMessage={setExecutionStatusMessage}
              messages={state.chatMessages}
              input={state.chatInput}
              onInputChange={setChatInput}
              executionStatus={executionStatus}
              initialInput={state.initialInstruction}
              busy={generating || state.running}
            />
          </div>
        </aside>
      </div>

      <div className="fixed bottom-6 right-6 z-30 flex flex-col items-end gap-3 lg:hidden">
        {!state.aiPanelOpen ? (
          <button
            type="button"
            onClick={() => update({ aiPanelOpen: true })}
            className="inline-flex h-11 items-center gap-2 rounded-full bg-slate-900 px-4 text-[13px] font-semibold text-white shadow-lg-token transition-colors hover:bg-slate-800"
            aria-label="Open AI assistant"
          >
            <Bot className="h-4 w-4" />
            AI Assistant
          </button>
        ) : null}

        {state.aiPanelOpen ? (
          <div className="fixed inset-0 z-40 flex flex-col bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <p className="text-h3">AI Assistant</p>
              <button
                type="button"
                onClick={() => update({ aiPanelOpen: false })}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-700 transition-colors hover:bg-slate-50"
                aria-label="Close AI assistant"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="flex-1 min-h-0 p-2">
              <AIChatPanel
                open
                targetUrl={state.targetUrl}
                testType={state.testType}
                testData={state.testData}
                currentPlan={activePlan}
                onPlanGenerated={handlePlanGenerated}
                onClearPlan={handleClearPlan}
                onAppendMessage={appendChat}
                onResetChat={resetChat}
                onInstructionUsed={(instruction) => update({ lastInstruction: instruction })}
                onExecutionStatusMessage={setExecutionStatusMessage}
                messages={state.chatMessages}
                input={state.chatInput}
                onInputChange={setChatInput}
                executionStatus={executionStatus}
                initialInput={state.initialInstruction}
                busy={generating || state.running}
              />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function RunTestForm({
  targetUrl,
  testName,
  formErrors,
  running,
  status,
  persisted,
  onTargetUrlChange,
  onTestNameChange,
  onRun,
  onNewTest,
}: {
  targetUrl: string;
  testName: string;
  formErrors: FormErrors;
  running: boolean;
  status: string;
  persisted: boolean;
  onTargetUrlChange: (value: string) => void;
  onTestNameChange: (value: string) => void;
  onRun: () => void;
  onNewTest: () => void;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs-token">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="space-y-1">
            <label className="block text-eyebrow">Target URL</label>
            <div className="relative">
              <LinkIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <Input
                type="url"
                value={targetUrl}
                onChange={(event) => onTargetUrlChange(event.target.value)}
                className={cn(
                  "h-9 w-full bg-slate-50 pl-9 focus-visible:bg-white",
                  formErrors.targetUrl
                    ? "border-red-300 focus-visible:border-red-500"
                    : undefined
                )}
                placeholder="Enter target URL"
              />
            </div>
            {formErrors.targetUrl ? (
              <p className="text-[11px] text-red-600">{formErrors.targetUrl}</p>
            ) : null}
          </div>

          <div className="space-y-1">
            <label className="block text-eyebrow">Test Name</label>
            <Input
              type="text"
              value={testName}
              onChange={(event) => onTestNameChange(event.target.value)}
              className={cn(
                "h-9 w-full bg-slate-50 focus-visible:bg-white",
                formErrors.testName
                  ? "border-red-300 focus-visible:border-red-500"
                  : undefined
              )}
              placeholder="Enter test name..."
            />
            {formErrors.testName ? (
              <p className="text-[11px] text-red-600">{formErrors.testName}</p>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2 lg:flex-col lg:items-end">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="default"
              onClick={onNewTest}
              title="Reset the workspace and start a new test"
              className="gap-1.5"
            >
              <FilePlus2 className="h-3.5 w-3.5" />
              New Test
            </Button>
            <Button
              onClick={onRun}
              disabled={running}
              size="default"
              className="gap-1.5"
            >
              <Play className="h-3.5 w-3.5" />
              {running ? "Running…" : "Run Test"}
            </Button>
          </div>
          <div className="flex items-center gap-2 text-[11.5px] text-slate-500">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold",
                statusTone(status)
              )}
            >
              <Lock className="h-3 w-3" />
              {persisted ? "Workspace restored" : "Workspace fresh"}
            </span>
            {persisted ? (
              <span className="inline-flex items-center gap-1 text-[10.5px] font-medium text-emerald-600">
                <Save className="h-3 w-3" />
                Auto-saved
              </span>
            ) : null}
          </div>
        </div>
      </div>
      {formErrors.goal ? (
        <p className="mt-2 text-[11.5px] text-red-600">{formErrors.goal}</p>
      ) : null}
    </section>
  );
}

function TestPlanPanel({
  plan,
  expanded,
  onToggleExpanded,
}: {
  plan: AIPlanResponse | null;
  expanded: boolean;
  onToggleExpanded: () => void;
}) {
  const planCases = getPlanCases(plan);
  const primaryCase = planCases[0] ?? null;
  const displaySteps = Array.isArray(primaryCase?.steps) ? primaryCase.steps : [];
  const executableStepCount = getGeneratedPlanStepCount(plan);

  return (
    <section
      className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token"
      style={{ minHeight: "32rem", flexBasis: "62%" }}
    >
      <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-h3">Generated Test Plan</h2>
            <span className="text-eyebrow text-slate-400">· Primary focus</span>
          </div>
          <p className="text-muted-sm">Scenario name, description, and steps only.</p>
        </div>
        <div className="flex items-center gap-2">
          {plan ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10.5px] font-semibold text-blue-700">
              <Sparkles className="h-3 w-3" />
              {executableStepCount} step{executableStepCount === 1 ? "" : "s"}
            </span>
          ) : null}
          <Button variant="outline" size="xs" onClick={onToggleExpanded}>
            {expanded ? "Collapse" : "Expand"}
          </Button>
        </div>
      </div>

      {expanded ? (
        <div className="flex-1 overflow-y-auto p-5">
          {plan ? (
            <div className="space-y-4">
              {plan.target_blocked ? (
                <BlockedTargetNotice
                  diagnostics={{
                    title: "Target blocked automation",
                    reason: plan.target_blocked_reason || "security_checkpoint",
                    message: "The target served a security checkpoint instead of the requested app page.",
                    is_testpulse_bug: false,
                    recommended_actions: [
                      "Use a staging or preview URL without bot protection.",
                      "Allowlist the Render backend or test user agent.",
                      "Confirm the page is reachable in a normal browser before re-running.",
                    ],
                  }}
                />
              ) : null}
              <div className="space-y-2 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-white p-4 shadow-xs-token">
                <p className="text-eyebrow">Scenario</p>
                <p className="text-[16px] font-semibold leading-snug text-slate-900">
                  {primaryCase?.title || "Untitled scenario"}
                </p>
                <p className="text-[13.5px] leading-relaxed text-slate-600">
                  {plan.summary || "No plan summary available."}
                </p>
                {plan.page_title ? (
                  <p className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11.5px] text-slate-500">
                    <span className="text-eyebrow text-slate-400">Page</span>
                    <span className="truncate font-medium text-slate-700">{plan.page_title}</span>
                  </p>
                ) : null}
              </div>

              <div className="space-y-2.5">
                <p className="text-eyebrow">Steps</p>
                {displaySteps.length > 0 ? (
                  <ol className="space-y-2.5">
                    {displaySteps.map((step, index) => (
                      <li
                        key={`${step.action ?? "step"}-${index}`}
                        className="flex gap-3.5 rounded-xl border border-slate-200 bg-white p-4 shadow-xs-token transition-colors hover:border-slate-300"
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-[13px] font-semibold text-primary">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1 space-y-2">
                          <p className="text-[14px] font-semibold leading-snug text-slate-900">
                            {step.action || "Step action"}
                          </p>
                          {step.target || step.selector || step.value ? (
                            <div className="grid gap-1.5 text-[12.5px] text-slate-600 sm:grid-cols-2">
                              {step.target ? (
                                <div className="rounded-md border border-slate-100 bg-slate-50/60 px-2.5 py-1.5">
                                  <p className="text-eyebrow text-slate-500">Target</p>
                                  <p className="break-words text-slate-800">{step.target}</p>
                                </div>
                              ) : null}
                              {step.selector ? (
                                <div className="rounded-md border border-slate-100 bg-slate-50/60 px-2.5 py-1.5">
                                  <p className="text-eyebrow text-slate-500">Selector</p>
                                  <p className="break-words font-mono text-[12px] text-slate-700">
                                    {step.selector}
                                  </p>
                                </div>
                              ) : null}
                              {step.value ? (
                                <div className="rounded-md border border-slate-100 bg-slate-50/60 px-2.5 py-1.5 sm:col-span-2">
                                  <p className="text-eyebrow text-slate-500">Value</p>
                                  <p className="break-words text-slate-800">{step.value}</p>
                                </div>
                              ) : null}
                            </div>
                          ) : (
                            <p className="text-[12.5px] text-slate-500">No step details provided.</p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-[12.5px] text-slate-500">
                    Plan has no executable steps yet.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-[600px] items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
              <div className="max-w-[22rem] space-y-2">
                <Sparkles className="mx-auto h-5 w-5 text-primary" />
                <p className="text-[13px] font-semibold text-slate-700">No plan generated yet</p>
                <p className="text-[12px] leading-relaxed text-slate-500">
                  Use the AI Copilot to generate a test plan. The plan, conversation, and execution state persist while you navigate.
                </p>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}

function BlockedTargetNotice({
  diagnostics,
}: {
  diagnostics?: TestApiResponse["blocked_diagnostics"] | null;
}) {
  if (!diagnostics) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[12.5px] text-amber-900">
      <div className="font-semibold">{diagnostics.title}</div>
      <div className="mt-1">{diagnostics.message}</div>
      <div className="mt-2 grid gap-1">
        {(diagnostics.recommended_actions ?? []).map((item) => (
          <div key={item} className="flex gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExecutionTerminal({
  terminalRef,
  logs,
  collapsed,
  onToggleCollapsed,
  follow,
  onToggleFollow,
  onScroll,
  status,
}: {
  terminalRef: React.RefObject<HTMLDivElement | null>;
  logs: TimelineRow[];
  collapsed: boolean;
  onToggleCollapsed: () => void;
  follow: boolean;
  onToggleFollow: () => void;
  onScroll: () => void;
  status: string;
}) {
  return (
    <section
      className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token min-h-[600px] flex-[2_1_600px]"
    >
      <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
        <div className="min-w-0">
          <h2 className="text-h3">Execution Terminal</h2>
          <p className="text-muted-sm">Live terminal-style logs from the current run.</p>
        </div>
        <div className="flex items-center gap-2">
          {status === "running" || status === "queued" || status === "planning" ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" />
              Live
            </span>
          ) : null}
          <button
            type="button"
            onClick={onToggleFollow}
            className={cn(
              "rounded-md border px-2 py-1 text-[11px] font-medium transition-colors",
              follow
                ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
            )}
            title={follow ? "Auto-scroll is on" : "Auto-scroll is off"}
          >
            {follow ? "Follow: on" : "Follow: off"}
          </button>
          <span
            className={cn(
              "rounded-full border px-2.5 py-1 text-[11px] font-medium",
              statusTone(status)
            )}
          >
            {statusLabel(status)}
          </span>
          <Button variant="outline" size="xs" onClick={onToggleCollapsed}>
            {collapsed ? "Expand" : "Collapse"}
          </Button>
        </div>
      </div>

      {!collapsed ? (
        <div
          ref={terminalRef}
          onScroll={onScroll}
          className="h-full min-h-[10rem] flex-1 overflow-y-auto bg-slate-950 px-4 py-3 font-mono text-[12.5px] text-slate-100"
        >
          <div className="space-y-1.5">
            {logs.length > 0 ? (
              logs.map((log, index) => (
                <div
                  key={`${log.time}-${index}`}
                  className="flex gap-2.5 rounded-md border border-slate-800/80 bg-slate-950/80 px-2.5 py-1.5 shadow-inner-token"
                >
                  <span className="shrink-0 text-slate-400">[{log.time}]</span>
                  <span className={`${log.color} w-16 shrink-0 font-bold`}>{log.level}</span>
                  <span className="break-words whitespace-pre-wrap text-slate-200">{log.text}</span>
                </div>
              ))
            ) : (
              <div className="rounded-md border border-dashed border-slate-800/80 bg-slate-950/80 px-3 py-3 text-slate-400">
                No execution logs yet. Start a test to see live output.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function useTestPolling(
  testId: string | null,
  enabled: boolean,
  setTestData: (data: TestApiResponse | null | ((prev: TestApiResponse | null) => TestApiResponse | null)) => void,
  setRunning: (running: boolean) => void
) {
  useEffect(() => {
    if (!enabled || !testId) return;

    let cancelled = false;

    let pollCount = 0;
    const mergePartial = (data: Partial<TestApiResponse>) => {
      setTestData((prev) => {
        const base = (prev ?? {}) as TestApiResponse;
        return { ...base, ...data } as TestApiResponse;
      });
    };

    const tick = async () => {
      try {
        pollCount += 1;
        const useFullPayload = pollCount === 1 || pollCount % 5 === 0;
        const data = useFullPayload
          ? ((await getTestById(testId)) as TestApiResponse)
          : ((await getTestStream(testId)) as Partial<TestApiResponse>);
        if (cancelled) return;
        if (useFullPayload) {
          setTestData(data as TestApiResponse);
        } else {
          mergePartial(data);
        }
        const status = (data.status ?? "").toLowerCase();
        const terminal = Boolean(data.is_terminal) || (status && status !== "running" && status !== "queued" && status !== "planning" && status !== "cancel_requested");
        if (terminal) {
          if (!useFullPayload) {
            const finalData = (await getTestById(testId)) as TestApiResponse;
            if (!cancelled) setTestData(finalData);
          }
          setRunning(false);
          return true;
        }
        return false;
      } catch (error) {
        console.error("Polling failed", error);
        return false;
      }
    };

    let timeout: number | null = null;
    const scheduleNext = () => {
      timeout = window.setTimeout(async () => {
        const finished = await tick();
        if (!cancelled && !finished) {
          scheduleNext();
        }
      }, 6000);
    };

    void (async () => {
      const done = await tick();
      if (cancelled) return;
      if (done) return;
      scheduleNext();
    })();

    void streamTestEvents(testId, async (event) => {
      if (cancelled) return;
      if (event.type === "snapshot") {
        mergePartial(event.data);
        const status = String(event.data.status || "").toLowerCase();
        if (event.data.is_terminal || (status && !["running", "queued", "planning", "cancel_requested"].includes(status))) {
          const finalData = (await getTestById(testId)) as TestApiResponse;
          if (!cancelled) setTestData(finalData);
          setRunning(false);
        }
      }
      if (event.type === "done") {
        const finalData = (await getTestById(testId)) as TestApiResponse;
        if (!cancelled) setTestData(finalData);
        setRunning(false);
      }
    }).catch((error) => {
      if (!cancelled) console.error("Execution stream failed; polling fallback remains active", error);
    });

    return () => {
      cancelled = true;
      if (timeout !== null) window.clearTimeout(timeout);
    };
  }, [testId, enabled, setTestData, setRunning]);
}
