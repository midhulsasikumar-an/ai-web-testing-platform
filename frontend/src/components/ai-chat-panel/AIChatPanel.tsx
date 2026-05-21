import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, RefreshCcw, Plus, ArrowRight } from 'lucide-react';

interface AIChatPanelProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const quickActions = [
  'Analyze Current Test',
  'Explain Failure',
  'Generate More Cases',
  'Create Workflow',
  'Find Similar Bugs',
  'Compare Previous Runs',
];

export default function AIChatPanel({ open, setOpen }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Array<{ from: 'user' | 'ai'; text: string }>>([
    { from: 'ai', text: 'Hi! I’m your testing copilot. Ask me about the current test, failures, reports, or workflows.' },
  ]);
  const [input, setInput] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(380);

  // Resizable handling within 360-420px range
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (panelRef.current) {
        const newWidth = Math.max(360, Math.min(420, window.innerWidth - e.clientX));
        setWidth(newWidth);
      }
    };
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    };
    const resizer = document.getElementById('ai-resizer');
    resizer?.addEventListener('mousedown', handleMouseDown);
    return () => {
      resizer?.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  // Header includes Current Context indicator
  const currentContext = "Current Test: Home Page";

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages([...messages, { from: 'user', text: input }]);
    setInput('');
    // Placeholder AI response
    setTimeout(() => {
      setMessages(prev => [...prev, { from: 'ai', text: 'Processing your request...' }]);
    }, 500);
  };

  if (!open) {
    return (
      <div
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-blue-600 text-white px-2 py-1 rounded-l-md cursor-pointer flex items-center gap-1"
        onClick={() => setOpen(true)}
      >
        <Bot className="h-4 w-4" /> AI
      </div>
    );
  }

  return (
    <aside
      ref={panelRef}
      style={{ width: `${width}px` }}
      className="flex flex-col bg-white/90 backdrop-blur-2xl border-l border-slate-200 shadow-lg rounded-l-lg transition-transform duration-300"
    >
      {/* Resizer Handle */}
      <div id="ai-resizer" className="absolute -left-1 top-0 h-full w-1 cursor-col-resize bg-transparent"></div>

      <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-white/50">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-amber-600">AI Copilot</h2>
          <span className="text-xs text-slate-500 ml-2">{currentContext}</span>
        </div>
        <div className="flex items-center gap-2">
          <button title="New Chat" className="text-slate-500 hover:text-slate-800">
            <Plus className="h-4 w-4" />
          </button>
          <button title="Clear Context" className="text-slate-500 hover:text-slate-800">
            <RefreshCcw className="h-4 w-4" />
          </button>
          <button title="Collapse" className="text-slate-500 hover:text-slate-800" onClick={() => setOpen(false)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 p-2 overflow-x-auto">
        {quickActions.map(action => (
          <button
            key={action}
            className="bg-blue-50 text-blue-600 text-xs px-2 py-1 rounded-full hover:bg-blue-100"
            onClick={() => setMessages([...messages, { from: 'user', text: action }])}
          >
            {action}
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-xs rounded-lg p-2 text-sm ${msg.from === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-900'}`}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="p-2 border-t border-slate-200 bg-white/50 flex items-center">
        <input
          type="text"
          placeholder="Ask AI about this test, failures, reports, workflows, or bugs..."
          className="flex-1 bg-slate-50 border border-slate-200 rounded-md py-1.5 pl-3 pr-10 text-sm text-slate-900 focus:outline-none focus:border-blue-500"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') sendMessage();
          }}
        />
        <button
          className="ml-2 text-blue-600 hover:text-blue-800"
          onClick={sendMessage}
          title="Send (Enter)"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
        <span className="ml-2 text-xs text-slate-500">Enter</span>
      </div>
    </aside>
  );
}
