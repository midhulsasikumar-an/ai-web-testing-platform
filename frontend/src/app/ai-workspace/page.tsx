"use client";

import { useState, useRef, useEffect } from "react";
import { API_BASE_URL } from "@/services/http";
import { Header } from "@/components/layout/header";
import { 
  Bot, 
  Send, 
  Paperclip, 
  Mic, 
  AlertTriangle, 
  Workflow, 
  ArrowRight,
  BarChart,
  Bug,
  Lightbulb,
  Shield,
  MousePointerClick,
  Activity,
  PlusCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function AIWorkspacePage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "I will create a reusable regression workflow prioritizing stability on critical transaction routes. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sendMessage = async (presetInput?: string) => {
    const textToSend = presetInput || input;
    if (!textToSend.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: textToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!presetInput) setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
      });

      if (!response.ok) throw new Error("Failed to fetch");
      const data = await response.json();

      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to AI backend. Please check if the backend is running." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-6">
      <Header title="AI Workspace" description="Collaborate with AI to generate workflows, analyze failures, and manage testing intelligence.">
        <button className="h-9 px-4 rounded-md border border-slate-300 bg-white text-slate-700 text-[13px] font-medium hover:bg-slate-50 transition-colors flex items-center gap-2">
          <PlusCircle className="h-4 w-4" />
          New Conversation
        </button>
      </Header>

      <div className="flex flex-col lg:flex-row gap-6 max-w-[1600px] mx-auto px-8">
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col gap-6">
          
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 flex-1 min-h-[600px]">
            {/* Chat Interface */}
            <section className="xl:col-span-2 flex flex-col bg-white/70 backdrop-blur-xl border border-slate-200 rounded-2xl shadow-sm overflow-hidden relative h-[80vh]">
              {/* Chat History */}
              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
                <div className="text-center">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Today, 10:42 AM</span>
                </div>

                {messages.map((msg, idx) => (
                  <div key={idx} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start items-start gap-3")}>
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 rounded bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0 mt-1">
                        <Bot className="h-5 w-5 text-blue-600" />
                      </div>
                    )}
                    
                    <div className={cn(
                      "px-5 py-3 rounded-2xl shadow-sm text-[14px]",
                      msg.role === "user" 
                        ? "bg-blue-50 border border-blue-100 rounded-tr-sm max-w-[80%] text-slate-800" 
                        : "bg-white border border-slate-200 rounded-tl-sm max-w-[90%] text-slate-800"
                    )}>
                      {msg.content}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start items-start gap-3 opacity-60">
                    <div className="w-8 h-8 rounded bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0 mt-1">
                      <Bot className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex gap-1 items-center">
                      <span className="w-2 h-2 rounded-full bg-blue-600/60 animate-bounce"></span>
                      <span className="w-2 h-2 rounded-full bg-blue-600/60 animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                      <span className="w-2 h-2 rounded-full bg-blue-600/60 animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-4 border-t border-slate-200 bg-white/90 backdrop-blur-md">
                <div className="flex flex-wrap gap-2 mb-3 px-2">
                  <button onClick={() => sendMessage("Generate regression workflow")} className="px-3 py-1 rounded-full border border-slate-200 bg-slate-50 hover:border-blue-300 text-slate-600 text-xs transition-colors">
                    Generate regression workflow
                  </button>
                  <button onClick={() => sendMessage("Analyze recurring bugs")} className="px-3 py-1 rounded-full border border-slate-200 bg-slate-50 hover:border-blue-300 text-slate-600 text-xs transition-colors">
                    Analyze recurring bugs
                  </button>
                  <button onClick={() => sendMessage("Suggest edge cases")} className="px-3 py-1 rounded-full border border-slate-200 bg-slate-50 hover:border-blue-300 text-slate-600 text-xs transition-colors">
                    Suggest edge cases
                  </button>
                </div>

                <div className="relative flex items-end bg-slate-50 border border-slate-200 rounded-xl overflow-hidden focus-within:border-blue-500 focus-within:shadow-sm transition-all">
                  <button className="p-3 text-slate-400 hover:text-blue-600 transition-colors">
                    <Paperclip className="h-5 w-5" />
                  </button>
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    className="w-full bg-transparent border-none text-slate-800 text-[14px] py-3 focus:ring-0 resize-none max-h-32 min-h-[44px] outline-none"
                    placeholder="Instruct the AI to build workflows, analyze logs..."
                    rows={1}
                  />
                  <div className="flex items-center p-2 gap-1">
                    <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors rounded-lg hover:bg-slate-100">
                      <Mic className="h-5 w-5" />
                    </button>
                    <button 
                      onClick={() => sendMessage()}
                      className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center shadow-sm"
                    >
                      <Send className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            </section>

            {/* Intelligence Panel */}
            <section className="flex flex-col gap-6">
              {/* Risk Prediction */}
              <div className="bg-white/70 backdrop-blur-xl rounded-xl p-5 border border-slate-200 border-l-4 border-l-amber-500 relative overflow-hidden shadow-sm">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                  <AlertTriangle className="h-16 w-16 text-amber-500" />
                </div>
                <h3 className="font-semibold text-slate-800 mb-1 text-[15px]">AI Risk Prediction</h3>
                <p className="text-sm text-slate-600 mb-4">High probability of failure detected in upcoming staging release.</p>
                
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono text-xs text-slate-700 font-medium">Checkout Flow API</span>
                    <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">87% Risk</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full rounded-full" style={{ width: '87%' }}></div>
                  </div>
                </div>
              </div>

              {/* Active Workflows */}
              <div className="bg-white/70 backdrop-blur-xl rounded-xl p-5 flex-1 border border-slate-200 shadow-sm flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-800 text-[15px]">Active Workflows</h3>
                  <button className="text-blue-600 hover:text-blue-700 text-xs font-medium">View All</button>
                </div>
                
                <div className="space-y-3">
                  <div className="p-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors cursor-pointer shadow-sm group">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-sm text-slate-800 font-medium truncate pr-2">Ecommerce Regression</span>
                      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Workflow className="h-3 w-3" /> 24 Steps
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-emerald-50 text-emerald-600 border border-emerald-100">
                        99% Stable
                      </span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors cursor-pointer shadow-sm group">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-sm text-slate-800 font-medium truncate pr-2">Login Stress Test</span>
                      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Workflow className="h-3 w-3" /> 8 Steps
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-50 text-amber-600 border border-amber-100">
                        72% Stable
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        {/* Right Aside (Quick Actions & Intel) */}
        <aside className="hidden lg:flex w-72 flex-col gap-8 shrink-0">
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Quick Actions</h4>
            <div className="grid grid-cols-2 gap-2">
              <button className="bg-white border border-slate-200 rounded-xl p-3 flex flex-col items-center justify-center gap-2 hover:border-blue-200 hover:bg-blue-50 transition-all shadow-sm group">
                <BarChart className="h-6 w-6 text-slate-400 group-hover:text-blue-600 transition-colors" />
                <span className="text-xs font-medium text-slate-700">Analyze Logs</span>
              </button>
              <button className="bg-white border border-slate-200 rounded-xl p-3 flex flex-col items-center justify-center gap-2 hover:border-blue-200 hover:bg-blue-50 transition-all shadow-sm group">
                <Bug className="h-6 w-6 text-slate-400 group-hover:text-blue-600 transition-colors" />
                <span className="text-xs font-medium text-slate-700">Find Bugs</span>
              </button>
            </div>
          </div>

          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <Lightbulb className="h-3.5 w-3.5 text-blue-500" />
              AI Intelligence
            </h4>
            <div className="p-3 rounded-lg border border-blue-100 bg-blue-50/50">
              <p className="text-sm text-slate-700 mb-2">Checkout flow showing increased instability in staging environment over last 48 hours.</p>
              <button className="text-blue-600 text-xs font-semibold hover:underline flex items-center gap-1">
                Generate Audit Test <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          </div>

          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Prompt Templates</h4>
            <ul className="space-y-1">
              <li>
                <button className="w-full text-left p-2.5 rounded-md hover:bg-slate-100 transition-colors flex items-center gap-3 group">
                  <Shield className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span className="text-sm font-medium text-slate-700">Security Audit Suite</span>
                </button>
              </li>
              <li>
                <button className="w-full text-left p-2.5 rounded-md hover:bg-slate-100 transition-colors flex items-center gap-3 group">
                  <MousePointerClick className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span className="text-sm font-medium text-slate-700">UX Interaction Analysis</span>
                </button>
              </li>
              <li>
                <button className="w-full text-left p-2.5 rounded-md hover:bg-slate-100 transition-colors flex items-center gap-3 group">
                  <Activity className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span className="text-sm font-medium text-slate-700">Performance Benchmark</span>
                </button>
              </li>
            </ul>
          </div>

          <div className="mt-auto pt-4 border-t border-slate-200">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Recent Contexts</h4>
            <ul className="space-y-1">
              <li><button className="w-full text-left py-1 text-slate-500 hover:text-blue-600 text-sm truncate">Fixing authentication timeout...</button></li>
              <li><button className="w-full text-left py-1 text-slate-500 hover:text-blue-600 text-sm truncate">Generate API payload tests</button></li>
            </ul>
          </div>
        </aside>

      </div>
    </div>
  );
}