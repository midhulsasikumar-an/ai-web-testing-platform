"use client";

import { Search, Plus, MessageSquare, MoreHorizontal, Trash2, PencilLine } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { AIChatSession } from "@/services/ai-workspace-api";

export type SessionBucket = "Today" | "Yesterday" | "Older";

export function formatRelativeBucket(value?: string): SessionBucket {
  if (!value) return "Older";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Older";
  const now = new Date();
  const diffDays = Math.floor(
    (Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) -
      Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) /
      86400000,
  );
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

export function formatSessionTime(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const bucket = formatRelativeBucket(value);
  if (bucket === "Today") {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (bucket === "Yesterday") {
    return "Yesterday";
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function groupSessions(sessions: AIChatSession[]): Record<SessionBucket, AIChatSession[]> {
  const groups: Record<SessionBucket, AIChatSession[]> = {
    Today: [],
    Yesterday: [],
    Older: [],
  };
  sessions.forEach((session) => {
    groups[formatRelativeBucket(session.updated_at)].push(session);
  });
  return groups;
}

interface ChatSidebarProps {
  sessions: AIChatSession[];
  activeSessionId: string | null;
  onOpenSession: (sessionId: string) => void;
  onNewChat: () => void;
  onRenameSession: (session: AIChatSession) => void;
  onDeleteSession: (session: AIChatSession) => void;
  className?: string;
  showBrand?: boolean;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  onOpenSession,
  onNewChat,
  onRenameSession,
  onDeleteSession,
  className,
  showBrand = false,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("");
  const needle = search.trim().toLowerCase();
  const filtered = !needle
    ? sessions
    : sessions.filter((item) => item.title.toLowerCase().includes(needle));
  const grouped = groupSessions(filtered);

  return (
    <aside
      className={cn(
        "flex h-full min-h-0 flex-col overflow-hidden bg-slate-50",
        className,
      )}
    >
      <div className={cn("flex flex-col gap-2 border-b border-slate-200/80 bg-white p-2.5", !showBrand && "pt-3")}>
        {showBrand ? (
          <div className="flex items-center gap-2 px-1 pb-1">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-xs-token">
              <MessageSquare className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-slate-900">AI Workspace</p>
              <p className="truncate text-[10.5px] text-slate-500">Test copilot & chat</p>
            </div>
          </div>
        ) : null}
        <button
          onClick={onNewChat}
          className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 text-[12.5px] font-medium text-white shadow-xs-token transition-all hover:bg-slate-800 active:scale-[0.99]"
        >
          <Plus className="h-3.5 w-3.5" />
          New Chat
        </button>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search conversations"
            className="h-8 w-full rounded-lg border border-slate-200 bg-slate-50 pl-8 pr-3 text-[12.5px] text-slate-800 outline-none transition-colors placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2">
        {(["Today", "Yesterday", "Older"] as const).map((bucket) => {
          const items = grouped[bucket];
          if (items.length === 0 && bucket !== "Today") return null;
          return (
            <div key={bucket} className="mb-3 last:mb-1">
              <p className="px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                {bucket}
              </p>
              <div className="space-y-0.5">
                {items.length === 0 ? (
                  <div className="rounded-md border border-dashed border-slate-200 bg-white/60 px-2.5 py-2.5 text-[11.5px] text-slate-500">
                    No conversations yet.
                  </div>
                ) : (
                  items.map((session) => (
                    <SessionItem
                      key={session.session_id}
                      session={session}
                      active={activeSessionId === session.session_id}
                      onOpen={() => onOpenSession(session.session_id)}
                      onRename={() => onRenameSession(session)}
                      onDelete={() => onDeleteSession(session)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function SessionItem({
  session,
  active,
  onOpen,
  onRename,
  onDelete,
}: {
  session: AIChatSession;
  active: boolean;
  onOpen: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  return (
    <div
      className={cn(
        "group relative flex items-center rounded-md transition-colors",
        active ? "bg-white shadow-xs-token" : "hover:bg-white/70",
      )}
    >
      {active ? <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-primary" /> : null}
      <button
        onClick={onOpen}
        className={cn(
          "flex w-full min-w-0 flex-col items-start gap-0.5 rounded-md px-2.5 py-1.5 text-left transition-colors",
          active ? "text-slate-900" : "text-slate-700",
        )}
      >
        <span className="line-clamp-1 w-full text-[12.5px] font-medium">{session.title || "New Chat"}</span>
        <span className="text-[10.5px] text-slate-500">{formatSessionTime(session.updated_at)}</span>
      </button>
      <div className="relative pr-1.5" ref={menuRef}>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className={cn(
            "inline-flex h-6 w-6 items-center justify-center rounded-md text-slate-400 transition-opacity hover:bg-slate-100 hover:text-slate-700",
            menuOpen || active ? "opacity-100" : "opacity-0 group-hover:opacity-100",
          )}
          aria-label="Conversation actions"
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </button>
        {menuOpen ? (
          <div className="absolute right-0 top-[calc(100%+4px)] z-30 w-32 origin-top-right overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg-token">
            <button
              onClick={() => {
                setMenuOpen(false);
                onRename();
              }}
              className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[12px] text-slate-700 hover:bg-slate-50"
            >
              <PencilLine className="h-3 w-3" />
              Rename
            </button>
            <button
              onClick={() => {
                setMenuOpen(false);
                onDelete();
              }}
              className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[12px] text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
