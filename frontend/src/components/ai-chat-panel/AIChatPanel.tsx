"use client";

import React, { useEffect, useMemo, useRef } from "react";
import type { AIPlanResponse, TestApiResponse } from "@/services/test-api";
import { generateTestPlan } from "@/services/test-api";
import { Bot, ChevronRight, Loader2, RefreshCw, Send, Sparkles, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/run-test-store";

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

  const executionState = normalizeStatus(executionStatus ?? testData?.status ?? testData?.overall_status ?? null);
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
  }, [messages]);

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
    if (busy) return;
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

      <div className="flex items-center gap-1.5 border-b border-slate-200 bg-slate-50/40 px-3.5 py-1.5">
        <button
          type="button"
          onClick={handleRefresh}
          disabled={busy}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", busy && "animate-spin")} />
          Refresh
        </button>
        <button
          type="button"
          onClick={handleNewChat}
          disabled={busy}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11.5px] font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <Trash2 className="h-3 w-3" />
          New chat
        </button>
        <span className="ml-auto text-[10.5px] text-slate-400">
          {messages.length} message{messages.length === 1 ? "" : "s"}
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
              disabled={busy || !input.trim()}
              title="Send"
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
