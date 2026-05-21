"use client";

import { Header } from "@/components/layout/header";
import { Play, Link as LinkIcon, BrainCircuit, Verified, Bot } from "lucide-react";
import { useState } from "react";
import AIChatPanel from "@/components/ai-chat-panel/AIChatPanel";

export default function RunTestPage() {
  // Top controls state
  const [targetUrl, setTargetUrl] = useState("");
  const [browser, setBrowser] = useState("Chrome (Headless)");
  const [device, setDevice] = useState("Desktop 1080p");



  // AI panel visibility
  const [aiPanelOpen, setAiPanelOpen] = useState(true);

  // Mock test plan data
  const testPlanSteps = [
    { id: 1, text: "Navigate to homepage and verify 200 OK", code: "page.goto('/')" },
    { id: 2, text: "Locate main navigation header", code: "expect(page.locator('nav')).toBeVisible()" },
    { id: 3, text: "Simulate user login flow with synthetic data", code: "ai.fillForm('#login', syntheticUser)" },
  ];

  // Mock terminal logs
  const terminalLogs = [
    { time: "14:02:01", level: "INFO", text: "Initializing testing environment...", color: "text-blue-500" },
    { time: "14:02:02", level: "INFO", text: "Launching Headless Chrome on Desktop 1080p profile.", color: "text-blue-500" },
    { time: "14:02:03", level: "WARN", text: "Slow network response from analytics provider, bypassing.", color: "text-amber-400" },
    { time: "14:02:05", level: "INFO", text: "Executing Step 1: Navigate homepage.", color: "text-blue-500" },
    { time: "14:02:06", level: "AI", text: "Detected dynamic DOM structure. Adjusting locators heuristically.", color: "text-cyan-400" },
    { time: "14:02:06", level: "INFO", text: "Locator identified: [data-testid=\"main-nav\"]", color: "text-blue-500" },
  ];

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
            <button className="bg-gradient-to-br from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white text-sm font-medium px-4 py-1 rounded-md flex items-center gap-1 shadow-[0_2px_6px_rgba(37,99,235,0.25)] transition-transform hover:scale-105">
              <Play className="h-4 w-4" />
              Run Test
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
                <Verified className="h-3 w-3" /> 98% Confidence
              </div>
            </div>
            <div className="space-y-2 flex-1">
              {testPlanSteps.map((step) => (
                <div key={step.id} className="flex items-start gap-3 bg-slate-50 p-2 rounded-md border border-slate-100 hover:border-blue-200 transition-colors">
                  <div className="bg-blue-100 text-blue-600 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                    {step.id}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800">{step.text}</p>
                    <p className="font-mono text-xs text-slate-500 mt-0.5">{step.code}</p>
                  </div>
                </div>
              ))}
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
              {terminalLogs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-blue-400 shrink-0">[{log.time}]</span>
                  <span className={`${log.color} font-bold w-12 shrink-0`}>{log.level}</span>
                  <span>{log.text}</span>
                </div>
              ))}
              <div className="flex gap-2 mt-3 animate-pulse">
                <span className="text-blue-400">[{new Date().toLocaleTimeString('en-GB', { hour12: false })}]</span>
                <span className="text-emerald-400 font-bold w-12">EXEC</span>
                <span className="flex items-center gap-2 text-slate-300">Awaiting next AI instruction...<span className="w-2 h-4 bg-emerald-400 inline-block shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span></span>
              </div>
            </div>
          </section>
        </div>

        {/* Right AI Copilot Panel */}
        <div className="relative border-l border-slate-200 pl-2">
          <AIChatPanel open={aiPanelOpen} setOpen={setAiPanelOpen} />
        </div>
      </div>
    </div>
  );
}
