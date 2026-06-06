import React from "react";
import { Terminal } from "lucide-react";

interface TerminalWindowProps {
  title: string;
  children: React.ReactNode;
}

export function TerminalWindow({ title, children }: TerminalWindowProps) {
  return (
    <div className="w-full max-w-[600px] mx-auto rounded-xl overflow-hidden shadow-2xl border border-[#2a2a2a] bg-[#1a1a1a] flex flex-col font-mono text-sm">
      {/* Top Bar (Mac window controls + title) */}
      <div className="h-10 bg-[#2d2d2d] flex items-center px-4 border-b border-[#111111] relative">
        <div className="flex gap-2 absolute left-4">
          <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
          <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
        </div>
        <div className="flex-1 text-center text-[#00f2fe] font-medium text-xs">
          {title}
        </div>
      </div>

      {/* Content Area */}
      <div className="p-8 text-[#e0e0e0]">
        {children}
      </div>

      {/* Footer Status Bar */}
      <div className="h-8 bg-[#2d2d2d] border-t border-[#111111] flex items-center justify-between px-4 text-[10px] text-gray-400 font-sans">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-[#27c93f]" />
            <span>CONNECTED</span>
          </div>
          <div className="flex items-center gap-1">
            <Terminal size={12} />
            <span>MAIN</span>
          </div>
        </div>
        <div>UTF-8</div>
      </div>
    </div>
  );
}