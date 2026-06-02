import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { AIPlanResponse, TestApiResponse } from '@/services/test-api';
import { generateTestPlan } from '@/services/test-api';
import { Bot, ChevronRight, Send, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AIChatPanelProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  targetUrl: string;
  testType: string;
  testData?: TestApiResponse | null;
  currentPlan?: AIPlanResponse | null;
  onPlanGenerated: (plan: AIPlanResponse) => void;
  onClearPlan: () => void;
  executionStatus?: string;
  initialInput?: string;
}

const INITIAL_MESSAGES = [
  { from: 'ai' as const, text: 'Hi! I’m your testing copilot. Ask me about the current test, failures, or reports.' },
];

function normalizeStatus(value?: string | null): string {
  const status = String(value ?? '').trim().toLowerCase();
  if (!status) return 'idle';
  if (['running', 'queued', 'planning'].includes(status)) return status;
  if (['completed', 'pass', 'passed', 'success'].includes(status)) return 'completed';
  if (['failed', 'fail', 'warning', 'timed_out', 'timeout', 'cancelled', 'cancel_requested'].includes(status)) return status;
  return status;
}

export default function AIChatPanel({ open, setOpen, targetUrl, testType, testData, currentPlan, onPlanGenerated, onClearPlan, executionStatus, initialInput }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Array<{ from: 'user' | 'ai'; text: string }>>(INITIAL_MESSAGES);
  const prevTestIdRef = useRef<string | null>(null);
  const lastInstructionRef = useRef<string>('');
  const [input, setInput] = useState(initialInput || '');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const executionState = normalizeStatus(executionStatus ?? testData?.status ?? testData?.overall_status ?? null);
  const currentContext = useMemo(() => {
    const url = String(targetUrl || testData?.target_url || testData?.url || '').trim();
    if (!url) {
      return 'Awaiting target URL';
    }

    try {
      return new URL(url.startsWith('http') ? url : `https://${url}`).hostname.replace(/^www\./, '');
    } catch {
      return url;
    }
  }, [targetUrl, testData?.target_url, testData?.url]);

  useEffect(() => {
    if (initialInput) {
      setInput(initialInput);
    }
  }, [initialInput]);

  useEffect(() => {
    const node = messagesRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) {
      return;
    }

    node.style.height = '0px';
    node.style.height = `${Math.min(Math.max(node.scrollHeight, 56), 180)}px`;
  }, [input]);

  const resetConversation = () => {
    prevTestIdRef.current = null;
    lastInstructionRef.current = '';
    setMessages(INITIAL_MESSAGES);
    setInput('');
  };

  const generatePlan = async (instruction: string, includeUserMessage = true) => {
    if (includeUserMessage) {
      setMessages((prev) => [...prev, { from: 'user', text: instruction }]);
    }
    setInput('');

    try {
      const plan = await generateTestPlan(targetUrl, instruction, testType);
      lastInstructionRef.current = instruction;
      onPlanGenerated(plan);
      setMessages((prev) => [
        ...prev,
        {
          from: 'ai',
          text: `${plan.summary} Generated ${plan.test_case.steps.length} executable step(s) for ${plan.page_title || targetUrl}.`,
        },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate a plan.';
      setMessages((prev) => [...prev, { from: 'ai', text: `AI plan request failed: ${message}` }]);
    }
  };

  const sendMessage = async (overrideInstruction?: string) => {
    const instruction = (overrideInstruction ?? input).trim();
    if (!instruction) return;
    if (!targetUrl.trim()) {
      setMessages((prev) => [...prev, { from: 'user', text: instruction }, { from: 'ai', text: 'Enter a target URL first so I can generate a real plan.' }]);
      setInput('');
      return;
    }

    await generatePlan(instruction, true);
  };

  const handleRefresh = async () => {
    const instruction = lastInstructionRef.current || (currentPlan?.instruction ?? '').trim();

    if (instruction && targetUrl.trim()) {
      await generatePlan(instruction, false);
      return;
    }

    setMessages(INITIAL_MESSAGES);
    setInput('');
    prevTestIdRef.current = null;
    if (!testData?.ai_plan) {
      setMessages((prev) => [...prev, { from: 'ai', text: 'Assistant state refreshed. Ask a question or generate a new plan.' }]);
    }
  };

  const handleNewChat = () => {
    resetConversation();
    onClearPlan();
  };

  // When testData changes, synthesize assistant messages from insights/results.
  useEffect(() => {
    if (!testData) return;
    const msgs: string[] = [];
    try {
      const executionId = (testData as TestApiResponse & { execution_id?: string }).execution_id;
      const id = (testData.test_id ?? executionId) as string | undefined || null;
      if (id && id === prevTestIdRef.current) return;
      prevTestIdRef.current = id ?? null;
      const status = (testData as TestApiResponse)['status'] as string | undefined;
      if (status) msgs.push(`Execution status: ${status}`);
      const aiSummary = (testData as TestApiResponse)['ai_summary'] as string | undefined;
      if (aiSummary) msgs.push(`AI: ${aiSummary}`);
      const insights = (testData as TestApiResponse)['insights'] as Record<string, unknown> | undefined;
      if (insights) {
        const critical = Array.isArray(insights['critical']) ? (insights['critical'] as unknown[]).length : 0;
        const moderate = Array.isArray(insights['moderate']) ? (insights['moderate'] as unknown[]).length : 0;
        if (critical) msgs.push(`Detected ${critical} critical issues.`);
        if (moderate) msgs.push(`Detected ${moderate} warnings.`);
      }
      const bugs = (testData as TestApiResponse)['bugs'] as unknown[] | undefined;
      if (Array.isArray(bugs) && bugs.length) msgs.push(`Created ${bugs.length} bug(s) from this run.`);

    } catch {
      // ignore
    }
    if (msgs.length) {
      setTimeout(() => {
        setMessages((prev) => [...prev, ...msgs.map((m) => ({ from: 'ai' as const, text: m }))]);
      }, 0);
    }
  }, [testData]);

  if (!open) {
    return (
      <div
        className="fixed right-0 top-1/2 z-40 -translate-y-1/2 rounded-l-xl border border-blue-200 bg-slate-900 px-3 py-2.5 text-white shadow-lg-token transition-transform hover:-translate-x-0.5"
        onClick={() => setOpen(true)}
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
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden">
      <div className="flex items-start gap-2.5 border-b border-slate-200 px-3.5 py-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-xs-token">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-h3">AI Copilot</h2>
          <p className="truncate text-muted-sm">{currentContext}</p>
        </div>
        <span className={cn(
          "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
          executionState === "running" || executionState === "queued" || executionState === "planning"
            ? "border-blue-200 bg-blue-50 text-blue-700"
            : "border-slate-200 bg-slate-50 text-slate-600"
        )}>
          {executionState}
        </span>
      </div>

      <div ref={messagesRef} className="flex-1 min-h-0 overflow-y-auto bg-slate-50/50 px-3.5 py-3.5">
        <div className="space-y-2.5">
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.from === 'user' ? 'flex justify-end' : 'flex justify-start'}>
              <div className={cn(
                'max-w-[92%] rounded-xl px-3 py-2 text-[12.5px] leading-relaxed',
                msg.from === 'user'
                  ? 'bg-blue-600 text-white shadow-xs-token'
                  : 'border border-slate-200 bg-white text-slate-900 shadow-xs-token'
              )}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>
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
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void sendMessage();
              }
            }}
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-[10.5px] text-slate-500">Enter to send · Shift+Enter for new line</p>
            <button
              className="inline-flex h-7 items-center justify-center gap-1.5 rounded-md bg-slate-900 px-2.5 text-[12px] font-medium text-white transition-colors hover:bg-slate-800"
              onClick={() => {
                void sendMessage();
              }}
              title="Send"
            >
              <Send className="h-3 w-3" />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
