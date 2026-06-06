"use client";

import { useEffect, useRef } from "react";
import { Send, Square, Paperclip, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatComposerProps {
  value: string;
  onChange: (next: string) => void;
  onSend: () => void;
  onStop?: () => void;
  loading?: boolean;
  placeholder?: string;
  className?: string;
  maxHeight?: number;
  showSuggestions?: boolean;
  suggestions?: { label: string; prompt: string }[];
  onSelectSuggestion?: (prompt: string) => void;
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  onStop,
  loading = false,
  placeholder = "Message AI assistant…",
  className,
  maxHeight = 220,
  showSuggestions = false,
  suggestions = [],
  onSelectSuggestion,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "0px";
    node.style.height = `${Math.min(Math.max(node.scrollHeight, 24), maxHeight)}px`;
  }, [value, maxHeight]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (loading && onStop) {
        onStop();
        return;
      }
      onSend();
    }
  };

  return (
    <div className={cn("w-full", className)}>
      {showSuggestions && suggestions.length > 0 && value.length === 0 ? (
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            Try
          </span>
          {suggestions.map((s) => (
            <button
              key={s.label}
              onClick={() => onSelectSuggestion?.(s.prompt)}
              className="inline-flex h-7 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 text-[11.5px] font-medium text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-primary"
            >
              <Sparkles className="h-3 w-3" />
              {s.label}
            </button>
          ))}
        </div>
      ) : null}

      <div
        className={cn(
          "rounded-2xl border border-slate-200 bg-white shadow-xs-token transition-all",
          "focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-500/15 focus-within:shadow-sm-token",
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          className="block w-full resize-none border-0 bg-transparent px-4 pb-1.5 pt-3 text-[13.5px] leading-relaxed text-slate-900 outline-none placeholder:text-slate-400"
        />
        <div className="flex items-center justify-between gap-2 px-2 pb-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Attach file"
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              title="Attach (coming soon)"
            >
              <Paperclip className="h-4 w-4" />
            </button>
          </div>
          <div className="flex items-center gap-1.5 pr-1 text-[10.5px] text-slate-400">
            <span className="hidden items-center gap-1 sm:inline-flex">
              <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 font-mono text-[10px] text-slate-500">Enter</kbd>
              to send
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="hidden items-center gap-1 sm:inline-flex">
              <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 font-mono text-[10px] text-slate-500">Shift</kbd>
              +
              <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 font-mono text-[10px] text-slate-500">Enter</kbd>
              for newline
            </span>
            {loading ? (
              <button
                onClick={onStop}
                className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-lg bg-slate-900 px-3 text-[12px] font-medium text-white shadow-xs-token transition-colors hover:bg-slate-800"
                title="Stop generating"
              >
                <Square className="h-3 w-3 fill-current" />
                Stop
              </button>
            ) : (
              <button
                onClick={onSend}
                disabled={!value.trim()}
                className={cn(
                  "ml-1 inline-flex h-8 w-8 items-center justify-center rounded-lg transition-all",
                  value.trim()
                    ? "bg-primary text-primary-foreground shadow-xs-token hover:bg-primary/90 active:scale-95"
                    : "bg-slate-100 text-slate-400 cursor-not-allowed",
                )}
                title="Send message"
                aria-label="Send message"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
