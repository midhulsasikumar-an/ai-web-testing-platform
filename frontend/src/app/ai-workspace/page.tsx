"use client";

import { useAuth } from "@/context/auth-context";
import { cn } from "@/lib/utils";
import {
  createChatSession,
  deleteChatSession,
  generateInstruction,
  getChatSession,
  listChatSessions,
  renameChatSession,
  sendChatMessageStream,
  type AIChatMessage,
  type AIChatResponse,
  type AIChatSession,
} from "@/services/ai-workspace-api";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Clock3,
  Copy,
  Loader2,
  Menu,
  PencilLine,
  Play,
  PlusCircle,
  RefreshCcw,
  Search,
  Send,
  Trash2,
  X,
  CheckCircle2,
} from "lucide-react";

const STORAGE_SESSION_KEY = "ai_workspace_active_session";
const STORAGE_PENDING_RUN_TEST_KEY = "ai_workspace_pending_run_test";
const CHAT_PHASES = [
  "Reading workspace context",
  "Retrieving related runs and bugs",
  "Model is composing",
  "Preparing final answer",
];

type SessionBucket = "Today" | "Yesterday" | "Older";
type UIIntent =
  | "general_chat"
  | "report_analysis"
  | "query_bugs"
  | "screenshot_analysis"
  | "instruction_generation"
  | "memory"
  | "memory_update"
  | "test_run_analysis"
  | "compare_runs"
  | string;

type UIMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  intent: UIIntent;
  retrievedData: unknown[];
  assistantPayload?: Record<string, unknown>;
};

function formatRelativeBucket(value?: string): SessionBucket {
  if (!value) return "Older";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Older";
  const now = new Date();
  const diffDays = Math.floor((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

function formatTime(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function deriveSessionTitle(prompt: string): string {
  const cleaned = prompt.trim().replace(/\s+/g, " ");
  if (!cleaned) return "New Chat";
  return cleaned.split(" ").slice(0, 6).join(" ");
}

function inferIntentFromHistory(message: AIChatMessage): UIIntent {
  if (message.role !== "assistant") {
    return "general_chat";
  }

  const text = String(message.content || "");
  const lowered = text.toLowerCase();

  if (text.includes("Test Objective:") && text.includes("Credentials:")) return "instruction_generation";
  if (lowered.startsWith("saved to memory:")) return "memory_update";
  if (lowered.startsWith("report analysis")) return "report_analysis";
  if (lowered.includes("matching bug") || lowered.startsWith("bug analysis")) return "query_bugs";
  if (lowered.includes("screenshot")) return "screenshot_analysis";
  return "general_chat";
}

function mapHistoryToUiMessages(history: AIChatMessage[]): UIMessage[] {
  return history.map((item, index) => ({
    id: `${item.timestamp}-${index}`,
    role: item.role,
    content: item.content,
    timestamp: item.timestamp,
    intent: inferIntentFromHistory(item),
    retrievedData: item.retrieved_data ?? [],
  }));
}

function parseInstructionTopic(prompt: string): string {
  const lowered = prompt.toLowerCase();
  for (const marker of ["for ", "about "]) {
    const index = lowered.indexOf(marker);
    if (index >= 0) {
      const topic = prompt.slice(index + marker.length).trim().replace(/[?.!]+$/, "");
      if (topic) return topic;
    }
  }
  return prompt.trim() || "the target website";
}

function buildAssistantUiMessage(result: AIChatResponse): UIMessage {
  return {
    id: `${new Date().toISOString()}-assistant`,
    role: "assistant",
    content: result.response,
    timestamp: new Date().toISOString(),
    intent: (result.intent || "general_chat") as UIIntent,
    retrievedData: result.retrieved_data ?? [],
    assistantPayload: result.assistant_payload,
  };
}

function getScreenshotPaths(data: unknown[]): string[] {
  return data
    .map((item) => {
      if (!item || typeof item !== "object") return "";
      const record = item as Record<string, unknown>;
      return String(record.path || record.url || record.artifact_url || "").trim();
    })
    .filter(Boolean)
    .slice(0, 5);
}

function getMessageText(data: unknown): string {
  if (!data || typeof data !== "object") return "";
  const record = data as Record<string, unknown>;
  return String(record.summary || record.report || record.message || record.status || "").trim();
}

export default function AIWorkspacePage() {
  const router = useRouter();
  useAuth();

  const [sessions, setSessions] = useState<AIChatSession[]>([]);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [conversationSearch, setConversationSearch] = useState("");
  const [input, setInput] = useState("");
  const [loadingChat, setLoadingChat] = useState(false);
  const [chatPhase, setChatPhase] = useState(CHAT_PHASES[0]);
  const [contextError, setContextError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [instructionDrafts, setInstructionDrafts] = useState<Record<string, string>>({});
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  const composerRef = useRef<HTMLTextAreaElement>(null);
  const messagesBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesBottomRef.current) {
      messagesBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loadingChat]);

  useEffect(() => {
    if (!loadingChat) {
      return undefined;
    }

    let index = 0;
    const interval = window.setInterval(() => {
      index = Math.min(index + 1, CHAT_PHASES.length - 1);
      setChatPhase(CHAT_PHASES[index]);
    }, 1400);

    return () => window.clearInterval(interval);
  }, [loadingChat]);

  useEffect(() => {
    const node = composerRef.current;
    if (!node) return;
    node.style.height = "0px";
    node.style.height = `${Math.min(Math.max(node.scrollHeight, 56), 220)}px`;
  }, [input]);

  useEffect(() => {
    let mounted = true;

    async function loadWorkspace() {
      try {
        const sessionList = await listChatSessions();
        if (!mounted) return;

        setSessions(sessionList);

        const storedSession = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_SESSION_KEY) : null;
        const nextSessionId = storedSession && sessionList.some((item) => item.session_id === storedSession)
          ? storedSession
          : sessionList[0]?.session_id ?? null;

        if (nextSessionId) {
          await openSession(nextSessionId);
        } else {
          setMessages([]);
          setActiveSessionId(null);
        }
      } catch (error) {
        setContextError(error instanceof Error ? error.message : "Failed to load AI workspace data.");
      }
    }

    async function openSession(sessionId: string) {
      const detail = await getChatSession(sessionId);
      if (!mounted) return;
      setActiveSessionId(sessionId);
      setMessages(mapHistoryToUiMessages(detail.history ?? []));
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_SESSION_KEY, sessionId);
      }
    }

    void loadWorkspace();
    return () => {
      mounted = false;
    };
  }, []);

  const groupedSessions = useMemo(() => {
    const needle = conversationSearch.trim().toLowerCase();
    const filtered = !needle
      ? sessions
      : sessions.filter((item) => item.title.toLowerCase().includes(needle));

    const groups: Record<SessionBucket, AIChatSession[]> = {
      Today: [],
      Yesterday: [],
      Older: [],
    };

    filtered.forEach((session) => {
      groups[formatRelativeBucket(session.updated_at)].push(session);
    });

    return groups;
  }, [conversationSearch, sessions]);

  const openSession = async (sessionId: string) => {
    const detail = await getChatSession(sessionId);
    setActiveSessionId(sessionId);
    setMessages(mapHistoryToUiMessages(detail.history ?? []));
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_SESSION_KEY, sessionId);
    }
    setSidebarOpen(false);
  };

  const refreshSessions = async () => {
    const nextSessions = await listChatSessions();
    setSessions(nextSessions);
    return nextSessions;
  };

  const newChat = async () => {
    const created = await createChatSession({ title: "New Chat" });
    setSessions((prev) => [created, ...prev.filter((item) => item.session_id !== created.session_id)]);
    setActiveSessionId(created.session_id);
    setMessages([]);
    setInput("");
    setSidebarOpen(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_SESSION_KEY, created.session_id);
    }
  };

  const handleRenameSession = async (session: AIChatSession) => {
    const nextTitle = window.prompt("Rename conversation", session.title);
    if (!nextTitle?.trim()) return;
    const updated = await renameChatSession(session.session_id, nextTitle.trim());
    setSessions((prev) => prev.map((item) => (item.session_id === updated.session_id ? updated : item)));
  };

  const handleDeleteSession = async (session: AIChatSession) => {
    const confirmed = window.confirm(`Delete conversation \"${session.title}\"?`);
    if (!confirmed) return;

    setContextError(null);
    setDeletingSessionId(session.session_id);
    try {
      await deleteChatSession(session.session_id);
      const next = sessions.filter((item) => item.session_id !== session.session_id);
      setSessions(next);

      if (activeSessionId === session.session_id) {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(STORAGE_SESSION_KEY);
        }
        if (next[0]?.session_id) {
          await openSession(next[0].session_id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
          setInput("");
          setInstructionDrafts({});
          setSidebarOpen(false);
        }
      }
      setSuccessToast("Conversation deleted");
      window.setTimeout(() => setSuccessToast(null), 1600);
    } catch (error) {
      setContextError(error instanceof Error ? error.message : "Failed to delete conversation.");
    } finally {
      setDeletingSessionId(null);
    }
  };

  const sendToRunTest = (instructionText: string, previousUserPrompt: string, title: string) => {
    const cleanInstruction = instructionText.trim();
    if (!cleanInstruction) return;

    const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/gi;
    let url = "";
    
    const promptMatch = previousUserPrompt.match(URL_REGEX);
    if (promptMatch && promptMatch.length > 0) {
      url = promptMatch[0];
    } else {
      const instructionMatch = cleanInstruction.match(URL_REGEX);
      if (instructionMatch && instructionMatch.length > 0) {
        url = instructionMatch[0];
      }
    }

    const payload = {
      url: url,
      instruction: cleanInstruction,
      source: "ai-workspace",
      session_id: activeSessionId || "",
      title: title || "AI Generated Test",
      created_at: new Date().toISOString()
    };

    console.log("Sending payload", payload);
    console.log("Payload instruction length:", payload.instruction?.length);
    window.localStorage.setItem(STORAGE_PENDING_RUN_TEST_KEY, JSON.stringify(payload));
    
    setSuccessToast("Instruction sent to Run Test!");
    setTimeout(() => {
      setSuccessToast(null);
      router.push("/run-test");
    }, 1000);
  };

  const copyMessage = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // no-op
    }
  };

  const submitMessage = async (override?: string, options?: { appendUser?: boolean }) => {
    const content = (override ?? input).trim();
    if (!content || loadingChat) return;

    setContextError(null);

    let sessionId = activeSessionId;
    if (!sessionId) {
      const created = await createChatSession({ title: deriveSessionTitle(content) });
      sessionId = created.session_id;
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(sessionId);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_SESSION_KEY, sessionId);
      }
    }

    const appendUser = options?.appendUser !== false;

    if (appendUser) {
      setMessages((prev) => [
        ...prev,
        {
          id: `${new Date().toISOString()}-user`,
          role: "user",
          content,
          timestamp: new Date().toISOString(),
          intent: "general_chat",
          retrievedData: [],
        },
      ]);
    }

    setInput("");
    setChatPhase(CHAT_PHASES[0]);
    setLoadingChat(true);

    try {
      const streamMessageId = `${new Date().toISOString()}-assistant-stream`;
      setMessages((prev) => [
        ...prev,
        {
          id: streamMessageId,
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString(),
          intent: "general_chat",
          retrievedData: [],
        },
      ]);

      const result = await sendChatMessageStream(
        { session_id: sessionId, message: content },
        (event) => {
          if (event.type === "status") {
            setChatPhase(event.message || CHAT_PHASES[0]);
            return;
          }
          if (event.type === "delta") {
            setMessages((prev) => prev.map((message) => (
              message.id === streamMessageId
                ? { ...message, content: `${message.content}${event.text}` }
                : message
            )));
            return;
          }
          if (event.type === "error") {
            setMessages((prev) => prev.map((message) => (
              message.id === streamMessageId
                ? { ...message, content: event.message }
                : message
            )));
          }
        }
      );
      const assistant = { ...buildAssistantUiMessage(result), id: streamMessageId };
      setMessages((prev) => prev.map((message) => (message.id === streamMessageId ? assistant : message)));

      if (assistant.intent === "instruction_generation") {
        setInstructionDrafts((prev) => ({ ...prev, [assistant.id]: assistant.content }));
      }

      const updatedSessions = await refreshSessions();
      const sessionRecord = updatedSessions.find((item) => item.session_id === sessionId);
      if (sessionRecord && sessionRecord.title === "New Chat") {
        const renamed = await renameChatSession(sessionId, deriveSessionTitle(content));
        setSessions((prev) => prev.map((item) => (item.session_id === renamed.session_id ? renamed : item)));
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to send message.";
      setMessages((prev) => [
        ...prev,
        {
          id: `${new Date().toISOString()}-assistant-error`,
          role: "assistant",
          content: message,
          timestamp: new Date().toISOString(),
          intent: "general_chat",
          retrievedData: [],
        },
      ]);
      setContextError(message);
    } finally {
      setLoadingChat(false);
    }
  };

  const regenerateResponse = async (assistantIndex: number) => {
    for (let idx = assistantIndex - 1; idx >= 0; idx -= 1) {
      if (messages[idx].role === "user") {
        await submitMessage(messages[idx].content, { appendUser: false });
        return;
      }
    }
  };

  const regenerateInstruction = async (messageId: string, fallbackPrompt: string) => {
    const topic = parseInstructionTopic(fallbackPrompt);
    const generated = await generateInstruction(topic);
    setInstructionDrafts((prev) => ({ ...prev, [messageId]: generated.instructions }));
    setMessages((prev) => prev.map((item) => (
      item.id === messageId
        ? {
            ...item,
            content: generated.instructions,
            assistantPayload: {
              ...(item.assistantPayload ?? {}),
              topic: generated.topic,
              instructions: generated.instructions,
            },
          }
        : item
    )));
  };

  const sidebar = (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
      <div className="space-y-2.5 border-b border-slate-200 p-3">
        <button
          onClick={() => void newChat()}
          className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 text-[13px] font-medium text-white shadow-xs-token transition-colors hover:bg-slate-800"
        >
          <PlusCircle className="h-4 w-4" />
          New Chat
        </button>
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2">
          <Search className="h-3.5 w-3.5 text-slate-400" />
          <input
            value={conversationSearch}
            onChange={(event) => setConversationSearch(event.target.value)}
            placeholder="Search conversations"
            className="w-full border-0 bg-transparent text-[13px] text-slate-800 outline-none placeholder:text-slate-400"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2.5">
        {(["Today", "Yesterday", "Older"] as const).map((bucket) => (
          <div key={bucket} className="mb-3 last:mb-0">
            <div className="mb-1.5 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-slate-400">{bucket}</div>
            <div className="space-y-1">
              {groupedSessions[bucket].length > 0 ? groupedSessions[bucket].map((session) => (
                <div
                  key={session.session_id}
                  className={cn(
                    "group rounded-lg border px-2.5 py-2 transition-colors",
                    activeSessionId === session.session_id ? "border-blue-200 bg-blue-50" : "border-transparent bg-white hover:bg-slate-50"
                  )}
                >
                  <button className="w-full text-left" onClick={() => void openSession(session.session_id)}>
                    <div className="truncate text-[12.5px] font-medium text-slate-900">{session.title}</div>
                    <div className="truncate text-[11px] text-slate-500">Updated {formatTime(session.updated_at) || formatDate(session.updated_at)}</div>
                  </button>
                  <div className="mt-1.5 flex items-center gap-1 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                    <button onClick={() => void handleRenameSession(session)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-1.5 py-0.5 text-[10.5px] text-slate-600 hover:bg-white">
                      <PencilLine className="h-3 w-3" />
                      Rename
                    </button>
                    <button
                      onClick={() => void handleDeleteSession(session)}
                      disabled={deletingSessionId === session.session_id}
                      className="inline-flex items-center gap-1 rounded-md border border-red-100 px-1.5 py-0.5 text-[10.5px] text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {deletingSessionId === session.session_id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                      {deletingSessionId === session.session_id ? "Deleting" : "Delete"}
                    </button>
                  </div>
                </div>
              )) : (
                <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-2.5 py-3 text-[12.5px] text-slate-500">No conversations yet.</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-[12.5px] font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            <Menu className="h-3.5 w-3.5" />
            Sessions
          </button>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => void newChat()}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-slate-900 px-3 text-[12.5px] font-medium text-white shadow-xs-token transition-colors hover:bg-slate-800"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            New Chat
          </button>
        </div>
      </div>

      <div className="grid h-full min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="hidden min-h-0 lg:block">{sidebar}</div>

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs-token">
          {successToast && (
            <div className="absolute left-1/2 top-4 z-50 flex -translate-x-1/2 items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-[13px] font-medium text-white shadow-lg-token transition-all animate-fade-in">
              <CheckCircle2 className="h-4 w-4" />
              {successToast}
            </div>
          )}
          <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3.5">
            <div>
              <h2 className="text-h3">Assistant Chat</h2>
              <p className="text-muted-sm">Ask naturally about memory, reports, bugs, screenshots, and instruction generation.</p>
            </div>
            {loadingChat ? (
              <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700">
                <Loader2 className="h-3 w-3 animate-spin" />
                {chatPhase}
              </div>
            ) : (
              <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                <Clock3 className="h-3 w-3" />
                Persisted conversations
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto bg-slate-50/40 px-4 py-4">
            {messages.length > 0 ? (
              <div className="space-y-3.5">
                {messages.map((message, index) => {
                  const isAssistant = message.role === "assistant";
                  const instructionText = instructionDrafts[message.id] ?? message.content;
                  const screenshotPaths = getScreenshotPaths(message.retrievedData);
                  const previousUserPrompt = (() => {
                    for (let i = index - 1; i >= 0; i -= 1) {
                      if (messages[i].role === "user") return messages[i].content;
                    }
                    return "";
                  })();

                  return (
                    <div key={message.id} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                      <div
                        className={cn(
                          "max-w-[95%] rounded-xl px-3.5 py-2.5 md:max-w-[88%]",
                          message.role === "user"
                            ? "bg-blue-600 text-white shadow-sm-token"
                            : "border border-slate-200 bg-white text-slate-900 shadow-xs-token"
                        )}
                      >
                        {isAssistant ? (
                          <div className="mb-1.5 flex items-center justify-between gap-2">
                            <div className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">
                              <Bot className="h-3 w-3" />
                              Assistant
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => void copyMessage(message.content)}
                                className="inline-flex h-6 items-center justify-center rounded-md border border-slate-200 px-1.5 text-[10.5px] text-slate-600 hover:bg-slate-50"
                                title="Copy message"
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                              <button
                                onClick={() => void regenerateResponse(index)}
                                className="inline-flex h-6 items-center justify-center rounded-md border border-slate-200 px-1.5 text-[10.5px] text-slate-600 hover:bg-slate-50"
                                title="Regenerate response"
                              >
                                <RefreshCcw className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                        ) : null}

                        {message.intent === "instruction_generation" ? (
                          <div className="space-y-2.5">
                            <textarea
                              value={instructionText}
                              onChange={(event) => setInstructionDrafts((prev) => ({ ...prev, [message.id]: event.target.value }))}
                              className="min-h-[220px] w-full resize-y rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12.5px] leading-relaxed text-slate-900 outline-none focus:border-blue-500"
                            />
                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                onClick={() => {
                                  const currentSession = sessions.find(s => s.session_id === activeSessionId);
                                  sendToRunTest(instructionText, previousUserPrompt, currentSession?.title || "");
                                }}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-blue-700"
                              >
                                <Play className="h-3 w-3" />
                                Send To Run Test
                              </button>
                              <button
                                onClick={() => void regenerateInstruction(message.id, previousUserPrompt || message.content)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
                              >
                                <RefreshCcw className="h-3 w-3" />
                                Regenerate
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap text-[13px] leading-relaxed">{message.content}</div>
                        )}

                        {isAssistant && message.intent === "report_analysis" ? (
                          <div className="mt-2.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-[12px] text-slate-700">
                            <div className="font-semibold text-slate-800">Report Analysis</div>
                            <div className="mt-1">Matched records: {message.retrievedData.length}</div>
                            {message.retrievedData[0] ? <div className="mt-1 text-slate-600">{getMessageText(message.retrievedData[0]) || "Report details included in response above."}</div> : null}
                          </div>
                        ) : null}

                        {isAssistant && message.intent === "query_bugs" ? (
                          <div className="mt-2.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-[12px] text-slate-700">
                            <div className="font-semibold text-slate-800">Bug Analysis</div>
                            <div className="mt-1">Matched bugs: {message.retrievedData.length}</div>
                          </div>
                        ) : null}

                        {isAssistant && message.intent === "screenshot_analysis" ? (
                          <div className="mt-2.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-[12px] text-slate-700">
                            <div className="font-semibold text-slate-800">Screenshot Analysis</div>
                            <div className="mt-1">Artifacts found: {screenshotPaths.length || message.retrievedData.length}</div>
                            {screenshotPaths.length > 0 ? (
                              <div className="mt-2 space-y-1">
                                {screenshotPaths.map((path) => (
                                  <div key={path} className="truncate rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]">{path}</div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ) : null}

                        {isAssistant && message.intent === "memory_update" ? (
                          <div className="mt-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-[12px] text-emerald-700">
                            <div className="font-semibold">Memory Saved</div>
                            <div className="mt-1">This preference is now persisted and will be used in future responses.</div>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                })}

                {loadingChat ? (
                  <div className="flex items-center gap-2.5 text-slate-500">
                    <div className="rounded-full border border-slate-200 bg-slate-50 p-1.5"><Bot className="h-3.5 w-3.5" /></div>
                    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-[12.5px] shadow-xs-token">
                      <span>{chatPhase}</span>
                      <span className="ml-1 inline-flex gap-0.5 align-middle">
                        <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500" />
                        <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500 [animation-delay:120ms]" />
                        <span className="h-1 w-1 animate-pulse rounded-full bg-blue-500 [animation-delay:240ms]" />
                      </span>
                    </div>
                  </div>
                ) : null}

                <div ref={messagesBottomRef} />
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-sm-token">
                  <Bot className="h-5 w-5" />
                </div>
                <div className="mb-1.5 text-h3">Start chatting with your AI assistant</div>
                <p className="max-w-md text-[12.5px] text-slate-500">Ask naturally: analyze latest report, summarize bugs, show screenshots, remember preferences, or generate test instructions.</p>
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 bg-white px-4 py-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2.5 transition-colors focus-within:border-blue-400 focus-within:bg-white">
              <textarea
                ref={composerRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void submitMessage();
                  }
                }}
                placeholder="Ask about reports, bugs, screenshots, instructions, testing strategies..."
                className="min-h-[56px] w-full resize-none border-0 bg-transparent px-1 py-1 text-[13px] text-slate-900 outline-none placeholder:text-slate-400"
                rows={1}
              />
              <div className="mt-2 flex items-center justify-between gap-2">
                <p className="text-[11px] text-slate-500">Enter to send, Shift+Enter for a new line</p>
                <button
                  onClick={() => void submitMessage()}
                  disabled={loadingChat || !input.trim()}
                  className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 text-[12.5px] font-medium text-white shadow-xs-token transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Send className="h-3.5 w-3.5" />
                  Send
                </button>
              </div>
            </div>
            {contextError ? (
              <div className="mt-2.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{contextError}</div>
            ) : null}
          </div>
        </main>
      </div>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar" />
          <div className="relative ml-auto h-full w-[88vw] max-w-[340px] p-3">
            <div className="mb-2 flex justify-end">
              <button
                onClick={() => setSidebarOpen(false)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 shadow-xs-token"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="h-[calc(100%-40px)]">{sidebar}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
