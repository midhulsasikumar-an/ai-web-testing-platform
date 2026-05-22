"use client";

import { Header } from "@/components/layout/header";
import { Play, Link as LinkIcon, BrainCircuit, Verified, Bot } from "lucide-react";
import { useState, useEffect } from "react";
import AIChatPanel from "@/components/ai-chat-panel/AIChatPanel";
import { startTest, getTestById, TestApiResponse, AIPlanResponse } from "@/services/test-api";
import { useAuth } from "@/context/auth-context";

export default function RunTestPage() {
  // Top controls state
  const [targetUrl, setTargetUrl] = useState("");
  const [browser, setBrowser] = useState("Chrome (Headless)");
  const [device, setDevice] = useState("Desktop 1080p");
  const [testType, setTestType] = useState("AI Generated Test");
  const [aiPlan, setAiPlan] = useState<AIPlanResponse | null>(null);
  useAuth();

  // Live test state
  const [testId, setTestId] = useState<string | null>(null);
  const [testData, setTestData] = useState<TestApiResponse | null>(null);
  const [running, setRunning] = useState(false);
  // start polling when testId changes
  useTestPolling(testId, setTestData, setRunning);



  // AI panel visibility
  const [aiPanelOpen, setAiPanelOpen] = useState(true);

  // Supported test types
  const TEST_TYPES = [
    "AI Generated Test",
    "Regression Test",
    "Accessibility Test",
    "Login Test",
    "Smoke Test",
    "Custom Test",
  ];

  // Derived logs from backend results or live backend stream logs
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

  const activePlan = testType === 'AI Generated Test' ? (aiPlan ?? testData?.ai_plan ?? null) : null;

  const handlePlanGenerated = (plan: AIPlanResponse) => {
    setAiPlan(plan);
  };

  const runTest = async () => {
    if (!targetUrl) {
      alert('Please enter a target URL');
      return;
    }

    try {
      setRunning(true);
      setTestData(null);
      setTestId(null);
      if (testType === 'AI Generated Test') {
        if (!activePlan) {
          alert('Ask the AI Copilot to generate a plan before running AI tests.');
          setRunning(false);
          return;
        }
        const res = await startTest(targetUrl, 'default', testType, activePlan);
        setTestId(res.test_id);
        return;
      }

      const res = await startTest(targetUrl, 'default', testType);
      setTestId(res.test_id);
    } catch (error) {
      console.error('Failed to start test', error);
      setRunning(false);
      alert('Failed to start test. See console for details.');
    }
  };

  return (
    <div className="bg-[#F8FAFC] min-h-screen flex flex-col relative overflow-hidden">
      <Header title="Workspace Controls">
        <button className="h-8 px-3 rounded-md border border-slate-300 bg-white text-blue-600 text-[12px] font-bold hover:border-blue-500 transition-colors">
          Deploy AI
        </button>
      </Header>

      <div className="flex-1 flex gap-4 max-w-[1440px] mx-auto w-full px-4 py-4">
        {/* Left / Main Workspace */}
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto">
          {/* Top configuration bar */}
          <section className="bg-white/80 backdrop-blur-xl border border-slate-200 rounded-xl p-3 flex flex-col md:flex-row gap-3 shadow-sm">
            <div className="relative flex-1 flex items-center">
              <LinkIcon className="absolute left-2 h-4 w-4 text-slate-400" />
              <input
                type="url"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                className="w-full bg-slate-50 border-b-2 border-slate-200 focus:border-blue-600 focus:bg-white py-2 pl-8 pr-3 text-sm text-slate-900 outline-none rounded-t"
                placeholder="Enter target URL"
              />
            </div>
            <select value={browser} onChange={(e) => setBrowser(e.target.value)} className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 text-sm text-slate-700 focus:border-blue-600 outline-none">
              <option>Chrome (Headless)</option>
              <option>Firefox</option>
              <option>Safari</option>
            </select>
            <select value={device} onChange={(e) => setDevice(e.target.value)} className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 text-sm text-slate-700 focus:border-blue-600 outline-none">
              <option>Desktop 1080p</option>
              <option>Mobile iOS</option>
              <option>Tablet Android</option>
            </select>
            <select value={testType} onChange={(e) => setTestType(e.target.value)} className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 text-sm text-slate-700 focus:border-blue-600 outline-none">
              {TEST_TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
            <button onClick={runTest} disabled={running} className="bg-gradient-to-br from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 disabled:opacity-60 disabled:hover:scale-100 text-white text-sm font-medium px-4 py-1 rounded-md flex items-center gap-1 shadow-[0_2px_6px_rgba(37,99,235,0.25)] transition-transform hover:scale-105">
              <Play className="h-4 w-4" />
              {running ? 'Running...' : 'Run Test'}
            </button>
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
        <div className="relative border-l border-slate-200 pl-2">
          <AIChatPanel
            open={aiPanelOpen}
            setOpen={setAiPanelOpen}
            targetUrl={targetUrl}
            testType={testType}
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
