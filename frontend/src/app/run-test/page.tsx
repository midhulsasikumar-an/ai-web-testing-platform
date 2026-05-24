"use client";

import { Header } from "@/components/layout/header";
import { Play, Link as LinkIcon, BrainCircuit, Verified, Bot } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import AIChatPanel from "@/components/ai-chat-panel/AIChatPanel";
import { startTest, getTestById, TestApiResponse, AIPlanResponse } from "@/services/test-api";
import { useAuth } from "@/context/auth-context";

type FormErrors = {
  targetUrl?: string;
  testName?: string;
  goal?: string;
};

function readLatestCopilotGoal(panelRoot: HTMLDivElement | null): string {
  if (!panelRoot) {
    return "";
  }

  const typedInput = panelRoot.querySelector('input[placeholder*="Ask AI about"]') as HTMLInputElement | null;
  const typedGoal = typedInput?.value?.trim() ?? "";
  if (typedGoal) {
    return typedGoal;
  }

  const userMessages = Array.from(panelRoot.querySelectorAll("div.bg-blue-600.text-white")) as HTMLElement[];
  const lastMessage = userMessages[userMessages.length - 1];
  return lastMessage?.textContent?.trim() ?? "";
}

export default function RunTestPage() {
  const [targetUrl, setTargetUrl] = useState("");
  const [testName, setTestName] = useState("");
  const [aiPlan, setAiPlan] = useState<AIPlanResponse | null>(null);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  useAuth();

  const [testId, setTestId] = useState<string | null>(null);
  const [testData, setTestData] = useState<TestApiResponse | null>(null);
  const [running, setRunning] = useState(false);
  useTestPolling(testId, setTestData, setRunning);

  const [aiPanelOpen, setAiPanelOpen] = useState(true);
  const aiPanelHostRef = useRef<HTMLDivElement | null>(null);

  const results = (testData?.results ?? []) as Array<Record<string, unknown>>;
  const streamLogs = testData?.stream_logs ?? [];
  const terminalLogs = streamLogs.length > 0
    ? streamLogs.map((entry) => ({
        time: entry.time,
        level: entry.level.toUpperCase(),
        text: entry.msg,
        color: entry.level === 'error' ? 'text-red-400' : entry.level === 'warn' ? 'text-amber-400' : 'text-blue-400',
      }))
    : results.map((r) => ({
    time: (r['time'] as string) ?? new Date().toLocaleTimeString('en-GB', { hour12: false }),
    level: ((r['status'] as string) ?? 'INFO').toUpperCase(),
    text: r['test'] ? `${String(r['test'])}: ${String(r['details'] ?? JSON.stringify(r))}` : JSON.stringify(r),
    color: (r['status'] === 'fail') ? 'text-red-400' : 'text-blue-400',
    }));

  const activePlan = aiPlan ?? testData?.ai_plan ?? null;

  const handlePlanGenerated = (plan: AIPlanResponse) => {
    setAiPlan(plan);
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
      const res = await startTest({
        url: normalizedUrl,
        testName: normalizedTestName,
        goal,
        aiPlan: activePlan,
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

  return (
    <div className="bg-[#F8FAFC] min-h-screen flex flex-col relative overflow-hidden">
      <Header title="Run Test" />

      <div className="flex-1 flex gap-4 max-w-[1440px] mx-auto w-full px-4 py-4">
        {/* Left / Main Workspace */}
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto">
          <section className="bg-white/80 backdrop-blur-xl border border-slate-200 rounded-xl p-4 grid grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto] gap-3 lg:gap-4 items-center shadow-sm">
            <div className="relative flex-1 flex items-center">
              <LinkIcon className="absolute left-2 h-4 w-4 text-slate-400" />
              <div className="w-full">
                <input
                  type="url"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className={`w-full h-10 bg-slate-50 border-b-2 ${formErrors.targetUrl ? 'border-red-300 focus:border-red-500' : 'border-slate-200 focus:border-blue-600'} focus:bg-white py-2 pl-8 pr-3 text-sm text-slate-900 outline-none rounded-t`}
                  placeholder="Enter target URL"
                />
                {formErrors.targetUrl ? <p className="mt-1 text-xs text-red-600">{formErrors.targetUrl}</p> : null}
              </div>
            </div>
            <div className="space-y-1">
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                className={`w-full h-10 bg-slate-50 border-b-2 ${formErrors.testName ? 'border-red-300 focus:border-red-500' : 'border-slate-200 focus:border-blue-600'} focus:bg-white py-2 px-3 text-sm text-slate-900 outline-none rounded-t`}
                placeholder="Enter test name..."
              />
              {formErrors.testName ? <p className="text-xs text-red-600">{formErrors.testName}</p> : null}
            </div>
            <div className="flex flex-col items-stretch justify-center gap-1">
              <button onClick={runTest} disabled={running} className="h-10 bg-gradient-to-br from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 disabled:opacity-60 disabled:hover:scale-100 text-white text-sm font-medium px-5 rounded-md flex items-center justify-center gap-1 shadow-[0_2px_6px_rgba(37,99,235,0.25)] transition-transform hover:scale-105 whitespace-nowrap">
                <Play className="h-4 w-4" />
                {running ? 'Running...' : 'Run Test'}
              </button>
              {formErrors.goal ? <p className="text-xs text-red-600 max-w-xs">{formErrors.goal}</p> : null}
            </div>
          </section>

          {/* Test Plan */}
          <section className="bg-white/80 backdrop-blur-xl border border-slate-200 rounded-xl p-4 flex flex-col shadow-sm max-h-[380px] overflow-y-auto">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-blue-600" />
                AI Generated Test Plan
              </h2>
              <div className="bg-amber-50 border border-amber-200 text-amber-700 text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1 uppercase tracking-wider">
                <Verified className="h-3 w-3" /> {(() => { const hs = testData?.health_score ?? null; return hs ? `${Math.round(hs)}% Confidence` : activePlan ? 'Plan Ready' : 'AI Confidence'; })()}
              </div>
            </div>
            <div className="space-y-2 flex-1">
              {activePlan ? (
                <div className="space-y-2">
                  <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                    <div className="text-sm font-semibold">Plan Title</div>
                    <div className="text-xs text-slate-500">{activePlan.test_case.title}</div>
                  </div>
                  <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                    <div className="text-sm font-semibold">Summary</div>
                    <div className="text-xs text-slate-500">{activePlan.summary}</div>
                  </div>
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {activePlan.test_case.steps.map((step, index) => (
                      <div key={`${step.action}-${index}`} className="p-2 bg-slate-50 rounded-md border border-slate-100">
                        <div className="text-sm font-semibold text-slate-800">Step {index + 1}: {step.action}</div>
                        <div className="text-xs text-slate-500 mt-1">{step.target || step.selector || 'No explicit target'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                    <div className="text-sm font-semibold">Target URL</div>
                    <div className="text-xs text-slate-500">{String(testData?.url ?? targetUrl) || '—'}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                      <div className="text-sm font-semibold">Execution Status</div>
                      <div className="text-xs text-slate-500">{String(testData?.status ?? (running ? 'running' : 'idle'))}</div>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                      <div className="text-sm font-semibold">Pages Discovered</div>
                      <div className="text-xs text-slate-500">{((testData?.artifacts as Record<string, unknown> | undefined)?.['dom_snapshots'] as unknown[] | undefined)?.length ?? 0}</div>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                      <div className="text-sm font-semibold">Forms Found</div>
                      <div className="text-xs text-slate-500">{((testData?.artifacts as Record<string, unknown> | undefined)?.['form_fuzzing'] as unknown[] | undefined)?.length ?? 0}</div>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-md border border-slate-100">
                      <div className="text-sm font-semibold">Buttons Tested</div>
                      <div className="text-xs text-slate-500">{results.filter((r)=> String(r['test'] ?? '').toLowerCase().includes('button')).length}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Execution Logs */}
          <section className="flex flex-col flex-1 min-h-[200px] bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-lg">
            <div className="flex border-b border-slate-700 bg-slate-800">
              {['Logs', 'Screenshots', 'Network', 'DOM'].map((tab, i) => (
                <button
                  key={tab}
                  className={`px-4 py-2 text-xs font-medium ${i === 0 ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/10' : 'text-slate-400 hover:text-white hover:bg-white/5'} transition-colors`}
                >
                  {tab}
                </button>
              ))}
              <button className="ml-auto px-4 py-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-white/5 flex items-center gap-1 transition-colors">
                <Bot className="h-4 w-4 text-blue-400" /> AI Analysis
              </button>
            </div>
            <div className="p-3 flex-1 overflow-y-auto font-mono text-sm text-slate-300 space-y-1">
              {terminalLogs.length > 0 ? terminalLogs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-blue-400 shrink-0">[{log.time}]</span>
                  <span className={`${log.color} font-bold w-12 shrink-0`}>{log.level}</span>
                  <span>{log.text}</span>
                </div>
              )) : (
                <div className="text-slate-500">No execution logs yet — start a test to see real-time activity.</div>
              )}
            </div>
          </section>
        </div>

        {/* Right AI Copilot Panel */}
        <div ref={aiPanelHostRef} className="relative border-l border-slate-200 pl-2">
          <AIChatPanel
            open={aiPanelOpen}
            setOpen={setAiPanelOpen}
            targetUrl={targetUrl}
            testType="AI Generated Test"
            testData={testData}
            onPlanGenerated={handlePlanGenerated}
          />
        </div>
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
