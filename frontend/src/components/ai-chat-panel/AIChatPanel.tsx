"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import type { AIPlanResponse, TestApiResponse } from "@/services/test-api";
import { generateTestPlan } from "@/services/test-api";
import { Bot, ChevronRight, Loader2, RefreshCw, Send, Sparkles, Trash2, BookOpen, LogIn, Search, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/run-test-store";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface AIChatPanelProps {
  open: boolean;
  setOpen?: (open: boolean) => void;
  targetUrl: string;
  testType: string;
  testData?: TestApiResponse | null;
  currentPlan?: AIPlanResponse | null;
  onPlanGenerated: (plan: AIPlanResponse) => void;
  onClearPlan: () => void;
  onAppendMessage: (message: ChatMessage) => void;
  onResetChat: () => void;
  onInstructionUsed: (instruction: string) => void;
  onExecutionStatusMessage: (status: string) => void;
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  executionStatus?: string;
  initialInput?: string;
  busy?: boolean;
}

const COPILOT_PHASES = [
  "Reading target page",
  "Discovering workflows",
  "Model is drafting steps",
  "Validating executable plan",
];

function normalizeStatus(value?: string | null): string {
  const status = String(value ?? "").trim().toLowerCase();
  if (!status) return "idle";
  if (["running", "queued", "planning"].includes(status)) return status;
  if (["completed", "pass", "passed", "success"].includes(status)) return "completed";
  if (["failed", "fail", "warning", "timed_out", "timeout", "cancelled", "cancel_requested"].includes(status)) return status;
  return status;
}

function createMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export default function AIChatPanel({
  open,
  setOpen,
  targetUrl,
  testType,
  testData,
  currentPlan,
  onPlanGenerated,
  onClearPlan,
  onAppendMessage,
  onResetChat,
  onInstructionUsed,
  onExecutionStatusMessage,
  messages,
  input,
  onInputChange,
  executionStatus,
  initialInput,
  busy = false,
}: AIChatPanelProps) {
  const prevTestIdRef = useRef<string | null>(null);
  const hasAppliedInitialRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copilotPhase, setCopilotPhase] = useState(COPILOT_PHASES[0]);

  const executionState = normalizeStatus(executionStatus ?? testData?.status ?? testData?.overall_status ?? null);
  const effectiveBusy = busy || isGenerating;
  const currentContext = useMemo(() => {
    const url = String(targetUrl || testData?.target_url || testData?.url || "").trim();
    if (!url) return "Awaiting target URL";
    try {
      return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
    } catch {
      return url;
    }
  }, [targetUrl, testData?.target_url, testData?.url]);

  useEffect(() => {
    if (!initialInput || hasAppliedInitialRef.current) return;
    onInputChange(initialInput);
    hasAppliedInitialRef.current = true;
  }, [initialInput, onInputChange]);

  useEffect(() => {
    const node = messagesRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, isGenerating, copilotPhase]);

  useEffect(() => {
    if (!isGenerating) {
      return undefined;
    }
    let index = 0;
    const interval = window.setInterval(() => {
      index = Math.min(index + 1, COPILOT_PHASES.length - 1);
      setCopilotPhase(COPILOT_PHASES[index]);
    }, 1300);
    return () => window.clearInterval(interval);
  }, [isGenerating]);

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "0px";
    node.style.height = `${Math.min(Math.max(node.scrollHeight, 56), 180)}px`;
  }, [input]);

  const generatePlan = async (instruction: string, includeUserMessage = true) => {
    if (includeUserMessage) {
      onAppendMessage({
        id: createMessageId(),
        from: "user",
        text: instruction,
        timestamp: Date.now(),
      });
    }
    onInputChange("");

    try {
      setCopilotPhase(COPILOT_PHASES[0]);
      setIsGenerating(true);
      const plan = await generateTestPlan(targetUrl, instruction, testType);
      onInstructionUsed(instruction);
      onPlanGenerated(plan);
      onAppendMessage({
        id: createMessageId(),
        from: "ai",
        text: `${plan.summary} Generated ${plan.test_case.steps.length} executable step(s) for ${plan.page_title || targetUrl}.`,
        timestamp: Date.now(),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate a plan.";
      onAppendMessage({
        id: createMessageId(),
        from: "ai",
        text: `AI plan request failed: ${message}`,
        timestamp: Date.now(),
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const sendMessage = async (overrideInstruction?: string) => {
    const instruction = (overrideInstruction ?? input).trim();
    if (!instruction) return;
    if (!targetUrl.trim()) {
      onAppendMessage({
        id: createMessageId(),
        from: "user",
        text: instruction,
        timestamp: Date.now(),
      });
      onAppendMessage({
        id: createMessageId(),
        from: "ai",
        text: "Enter a target URL first so I can generate a real plan.",
        timestamp: Date.now(),
      });
      onInputChange("");
      return;
    }
    await generatePlan(instruction, true);
  };

  const handleRefresh = async () => {
    if (effectiveBusy) return;
    const instruction = currentPlan?.instruction?.trim() ?? "";
    if (instruction && targetUrl.trim()) {
      await generatePlan(instruction, false);
      return;
    }
    onAppendMessage({
      id: createMessageId(),
      from: "ai",
      text: "Assistant state refreshed. Ask a question or generate a new plan.",
      timestamp: Date.now(),
    });
  };

  const handleNewChat = () => {
    onResetChat();
    onClearPlan();
  };

  useEffect(() => {
    if (!testData) return;
    const id = (testData.test_id ?? (testData as { execution_id?: string }).execution_id ?? null) as string | null;
    if (id && id === prevTestIdRef.current) return;
    prevTestIdRef.current = id ?? null;

    const msgs: { text: string }[] = [];
    const aiSummary = (testData as TestApiResponse).ai_summary as string | undefined;
    if (aiSummary) msgs.push({ text: `AI: ${aiSummary}` });
    const insights = (testData as TestApiResponse).insights as Record<string, unknown> | undefined;
    if (insights) {
      const critical = Array.isArray(insights.critical) ? (insights.critical as unknown[]).length : 0;
      const moderate = Array.isArray(insights.moderate) ? (insights.moderate as unknown[]).length : 0;
      if (critical) msgs.push({ text: `Detected ${critical} critical issues.` });
      if (moderate) msgs.push({ text: `Detected ${moderate} warnings.` });
    }
    const bugs = (testData as TestApiResponse).bugs as unknown[] | undefined;
    if (Array.isArray(bugs) && bugs.length) msgs.push({ text: `Created ${bugs.length} bug(s) from this run.` });

    if (msgs.length) {
      const t = window.setTimeout(() => {
        msgs.forEach((entry) => {
          onAppendMessage({
            id: createMessageId(),
            from: "ai",
            text: entry.text,
            timestamp: Date.now(),
          });
        });
      }, 0);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [testData, onAppendMessage]);

  useEffect(() => {
    if (executionState === "idle" || !executionState) return;
    onExecutionStatusMessage(executionState);
  }, [executionState, onExecutionStatusMessage]);

  if (!open) {
    return (
      <div
        className="fixed right-0 top-1/2 z-40 -translate-y-1/2 rounded-l-xl border border-blue-200 bg-slate-900 px-3 py-2.5 text-white shadow-lg-token transition-transform hover:-translate-x-0.5"
        onClick={() => setOpen?.(true)}
      >
        <div className="flex items-center gap-1.5">
          <Bot className="h-3.5 w-3.5" />
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]">AI</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
      <div className="flex items-start gap-2.5 border-b border-slate-200 px-3.5 py-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-xs-token">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-h3">AI Copilot</h2>
          <p className="truncate text-muted-sm">{currentContext}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <ExampleFormatDialog />
          <span
            className={cn(
              "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
              executionState === "running" || executionState === "queued" || executionState === "planning"
                ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-slate-200 bg-slate-50 text-slate-600"
            )}
          >
            {executionState}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 border-b border-slate-200 bg-slate-50/40 px-3.5 py-1.5">
        <button
          type="button"
          onClick={handleRefresh}
          disabled={effectiveBusy}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", busy && "animate-spin")} />
          Refresh
        </button>
        <button
          type="button"
          onClick={handleNewChat}
          disabled={effectiveBusy}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <Trash2 className="h-3 w-3" />
          New chat
        </button>
        <span className="ml-auto text-[10.5px] text-slate-400">
          {isGenerating ? copilotPhase : `${messages.length} message${messages.length === 1 ? "" : "s"}`}
        </span>
      </div>

      <div ref={messagesRef} className="flex-1 min-h-0 overflow-y-auto bg-slate-50/40 px-3.5 py-3.5">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center">
            <div className="max-w-[18rem] space-y-1.5">
              <p className="text-[12.5px] font-medium text-slate-700">No messages yet</p>
              <p className="text-[11.5px] leading-relaxed text-slate-500">
                Ask the copilot to generate a plan, summarise the run, or recommend next steps. Your conversation persists while you navigate.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2.5">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn("flex", msg.from === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[92%] rounded-xl px-3 py-2 text-[12.5px] leading-relaxed shadow-xs-token",
                    msg.from === "user"
                      ? "bg-blue-600 text-white"
                      : "border border-slate-200 bg-white text-slate-900"
                  )}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {isGenerating ? (
              <div className="flex justify-start">
                <div className="max-w-[92%] rounded-xl border border-blue-100 bg-white px-3 py-2 text-[12.5px] leading-relaxed text-slate-700 shadow-xs-token">
                  <span>{copilotPhase}</span>
                  <span className="ml-1 inline-flex gap-0.5 align-middle">
                    <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500" />
                    <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500 [animation-delay:120ms]" />
                    <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500 [animation-delay:240ms]" />
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white p-2.5">
        <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-2 shadow-xs-token">
          <label className="mb-1.5 block text-eyebrow">Ask the assistant</label>
          <textarea
            ref={textareaRef}
            rows={2}
            placeholder="Ask about failures, next steps, flaky areas, reports, or generate a new plan..."
            className="min-h-[56px] w-full resize-none rounded-md border border-slate-200 bg-white px-2.5 py-2 text-[12.5px] text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-blue-500"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendMessage();
              }
            }}
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-[10.5px] text-slate-500">Enter to send · Shift+Enter for new line</p>
            <button
              className="inline-flex h-7 items-center justify-center gap-1.5 rounded-md bg-slate-900 px-2.5 text-[12px] font-medium text-white transition-colors hover:bg-slate-800 disabled:opacity-50"
              onClick={() => {
                void sendMessage();
              }}
              disabled={effectiveBusy || !input.trim()}
              title="Send"
            >
              {effectiveBusy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Example Format dialog (documentation only)
//
// Shows three generic, reusable test workflow examples inside the AI Copilot
// header. This is documentation, not an input mechanism. The popover NEVER
// touches the chat input, never calls onInputChange, and never modifies
// the user's text -- it just displays reference material.
// ---------------------------------------------------------------------------

interface ExampleWorkflow {
  id: "login" | "search" | "form";
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  website: string;
  objective: string;
  credentials?: { username: string; password: string };
  steps: string[];
  expectedResult: string;
}

const EXAMPLE_WORKFLOWS: ExampleWorkflow[] = [
  {
    id: "login",
    title: "Login workflow",
    icon: LogIn,
    website: "https://www.abc.xyz/login",
    objective: "Sign in with valid credentials and reach the authenticated landing page.",
    credentials: { username: "demo_user", password: "Demo!Pass123" },
    steps: [
      "Open the login page.",
      "Type the username into the username field.",
      "Type the password into the password field.",
      "Click the Sign In button.",
      "Wait for the dashboard to finish loading.",
    ],
    expectedResult: "The user is redirected to the dashboard at /home with the profile menu visible in the top-right corner.",
  },
  {
    id: "search",
    title: "Search workflow",
    icon: Search,
    website: "https://www.abc.xyz/search",
    objective: "Submit a search query and confirm relevant results render in the results list.",
    steps: [
      "Open the search page.",
      "Type the query into the search input.",
      "Press the Search button (or hit Enter).",
      "Wait for the result list to render.",
    ],
    expectedResult: "At least one result card is visible and each card shows a title, snippet, and link.",
  },
  {
    id: "form",
    title: "Form submission workflow",
    icon: FileText,
    website: "https://www.abc.xyz/contact",
    objective: "Fill the contact form with valid data and verify the success confirmation appears.",
    steps: [
      "Open the contact form page.",
      "Type a name into the Full Name field.",
      "Type a valid email into the Email field.",
      "Type a short message into the Message field.",
      "Click the Submit button.",
      "Wait for the confirmation banner to appear.",
    ],
    expectedResult: "A success banner is shown with the text 'Thanks, we received your message' and the form is reset.",
  },
];

function ExampleFormatDialog() {
  return (
    <Dialog>
      <DialogTrigger
        render={
          <button
            type="button"
            aria-label="View example workflow formats"
            className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-50"
          >
            <BookOpen className="h-3 w-3" />
            Example Format
          </button>
        }
      />
      <DialogContent
        showCloseButton
        className="sm:max-w-2xl max-h-[85vh] overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle>Example Workflow Format</DialogTitle>
          <DialogDescription>
            Three reusable structures for the AI Copilot. These are reference
            examples only -- nothing here fills the chat input. Type your own
            instruction based on the shape that fits your goal.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {EXAMPLE_WORKFLOWS.map((workflow) => {
            const Icon = workflow.icon;
            return (
              <article
                key={workflow.id}
                className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs-token"
              >
                <header className="mb-2 flex items-center gap-1.5">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-600">
                    <Icon className="h-3 w-3" />
                  </span>
                  <h3 className="text-[12.5px] font-semibold text-slate-900">
                    {workflow.title}
                  </h3>
                </header>

                <dl className="space-y-1.5 text-[12px] leading-relaxed">
                  <DefinitionRow label="Website">
                    <code className="rounded bg-slate-50 px-1 py-0.5 font-mono text-[11.5px] text-slate-700">
                      {workflow.website}
                    </code>
                  </DefinitionRow>
                  <DefinitionRow label="Objective">
                    {workflow.objective}
                  </DefinitionRow>
                  {workflow.credentials ? (
                    <DefinitionRow label="Credentials">
                      <span className="font-mono text-[11.5px] text-slate-700">
                        {workflow.credentials.username} / {workflow.credentials.password}
                      </span>
                    </DefinitionRow>
                  ) : null}
                  <DefinitionRow label="Steps">
                    <ol className="list-decimal space-y-0.5 pl-4 text-slate-700">
                      {workflow.steps.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                  </DefinitionRow>
                  <DefinitionRow label="Expected Result">
                    {workflow.expectedResult}
                  </DefinitionRow>
                </dl>
              </article>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DefinitionRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-0.5 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-2">
      <dt className="text-eyebrow text-slate-500">{label}</dt>
      <dd className="min-w-0 text-slate-800">{children}</dd>
    </div>
  );
}

