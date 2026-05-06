"use client";

import { LOG_LEVEL_COLORS, LOG_LEVEL_ICONS } from "@/lib/constants";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────

interface LogLine {
  time: string;
  level: string;
  msg: string;
}

interface TerminalLogProps {
  /** Array of log entries to render */
  entries: LogLine[];
  /** Max height of the scrollable container (Tailwind class) */
  maxHeight?: string;
  /** Whether to show a blinking cursor at the bottom */
  showCursor?: boolean;
  /** Optional className for the outer container */
  className?: string;
  /** Optional ref for scroll-to-bottom behavior */
  scrollRef?: React.RefObject<HTMLDivElement | null>;
}

// ── Component ──────────────────────────────────────────────────────

export function TerminalLog({
  entries,
  maxHeight = "max-h-64",
  showCursor = false,
  className,
  scrollRef,
}: TerminalLogProps) {
  return (
    <div
      ref={scrollRef}
      className={cn(
        "rounded-lg bg-[#0d1117] p-4 overflow-y-auto terminal-log",
        maxHeight,
        className
      )}
    >
      {entries.map((entry, i) => (
        <div key={i} className="flex gap-2 py-0.5 leading-relaxed">
          <span className="log-timestamp shrink-0 select-none">
            [{entry.time}]
          </span>
          <span
            className={`shrink-0 w-3 text-center select-none ${LOG_LEVEL_COLORS[entry.level] ?? ""}`}
          >
            {LOG_LEVEL_ICONS[entry.level] ?? "·"}
          </span>
          <span className={LOG_LEVEL_COLORS[entry.level] ?? ""}>
            {entry.msg}
          </span>
        </div>
      ))}
      {showCursor && (
        <div className="flex gap-2 py-0.5 mt-1">
          <span className="log-timestamp select-none">[--:--]</span>
          <span className="log-info animate-pulse">▌</span>
        </div>
      )}
    </div>
  );
}
