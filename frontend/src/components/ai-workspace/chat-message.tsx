"use client";

import { useMemo, useState } from "react";
import { Copy, RefreshCw, ThumbsUp, ThumbsDown, Check, Play, FileText, Bug as BugIcon, Image as ImageIcon, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import { AvatarBot, IntentChip, MetaTimestamp, type UIMessage, getIntentMeta } from "./chat-primitives";

interface ChatMessageProps {
  message: UIMessage;
  isFirstInGroup?: boolean;
  isLastInGroup?: boolean;
  onCopy?: (text: string) => void;
  onRegenerate?: () => void;
  onSendToRunTest?: (text: string, fallbackPrompt: string) => void;
  onRegenerateInstruction?: (messageId: string, fallbackPrompt: string) => void;
  onEditDraft?: (messageId: string, text: string) => void;
  draftText?: string;
  previousUserPrompt?: string;
}

export function ChatMessage({
  message,
  isFirstInGroup = true,
  isLastInGroup = true,
  onCopy,
  onRegenerate,
  onSendToRunTest,
  onRegenerateInstruction,
  onEditDraft,
  draftText,
  previousUserPrompt,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const screenshotPaths = useMemo(() => {
    if (message.intent !== "screenshot_analysis") return [];
    return message.retrievedData
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const record = item as Record<string, unknown>;
        return String(record.path || record.url || record.artifact_url || "").trim();
      })
      .filter(Boolean)
      .slice(0, 5);
  }, [message.intent, message.retrievedData]);

  if (message.role === "user") {
    return (
      <div className={cn("flex w-full justify-end", !isFirstInGroup && "mt-1")}>
        <div className="max-w-[88%] sm:max-w-[78%]">
          <div
            className={cn(
              "rounded-2xl rounded-br-md bg-primary px-3.5 py-2.5 text-[13.5px] leading-relaxed text-primary-foreground shadow-xs-token",
              isFirstInGroup ? "rounded-tr-2xl" : "rounded-tr-2xl",
            )}
          >
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          {isLastInGroup ? (
            <div className="mt-1 flex justify-end pr-1">
              <MetaTimestamp value={message.timestamp} />
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  const intentMeta = getIntentMeta(message.intent);
  const isInstruction = message.intent === "instruction_generation";
  const instructionText = isInstruction ? (draftText ?? message.content) : "";

  const handleCopy = async () => {
    if (!onCopy) return;
    await onCopy(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={cn("flex w-full items-start gap-3", !isFirstInGroup && "mt-2")}>
      <div className="pt-0.5">
        <AvatarBot tone={intentMeta.tone === "slate" ? "blue" : (intentMeta.tone as "blue" | "violet" | "red" | "emerald")} size="md" />
      </div>
      <div className="min-w-0 flex-1">
        {isFirstInGroup ? (
          <div className="mb-1.5 flex items-center gap-2">
            <span className="text-[12.5px] font-semibold text-slate-900">Assistant</span>
            <IntentChip intent={message.intent} />
            <MetaTimestamp value={message.timestamp} />
          </div>
        ) : null}

        {isInstruction ? (
          <div className="space-y-2.5">
            <textarea
              value={instructionText}
              onChange={(event) => onEditDraft?.(message.id, event.target.value)}
              className="min-h-[180px] w-full resize-y rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-3 text-[13px] leading-relaxed text-slate-900 outline-none transition-colors focus:border-blue-300 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
            />
            <div className="flex flex-wrap items-center gap-2">
              {onSendToRunTest ? (
                <button
                  onClick={() => onSendToRunTest(instructionText, previousUserPrompt || "")}
                  disabled={!instructionText.trim()}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-[12.5px] font-semibold text-primary-foreground shadow-xs-token transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                  <Play className="h-3 w-3 fill-current" />
                  Send to Run Test
                </button>
              ) : null}
              {onRegenerateInstruction ? (
                <button
                  onClick={() => onRegenerateInstruction(message.id, previousUserPrompt || message.content)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[12.5px] font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  <RefreshCw className="h-3 w-3" />
                  Regenerate
                </button>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="prose prose-slate max-w-none whitespace-pre-wrap break-words text-[13.5px] leading-relaxed text-slate-800">
            {message.content}
          </div>
        )}

        {message.intent === "report_analysis" && message.retrievedData.length > 0 ? (
          <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50/60 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11.5px] font-semibold uppercase tracking-[0.14em] text-primary">
              <FileText className="h-3 w-3" />
              Report Analysis
            </div>
            <div className="text-[12px] text-slate-700">
              <span className="font-semibold">{message.retrievedData.length}</span> matched record(s)
            </div>
            {message.retrievedData[0] ? (
              <div className="mt-1.5 line-clamp-3 text-[12px] text-slate-600">
                {String((message.retrievedData[0] as Record<string, unknown>).summary || (message.retrievedData[0] as Record<string, unknown>).report || "Report details included in response above.")}
              </div>
            ) : null}
          </div>
        ) : null}

        {message.intent === "query_bugs" && message.retrievedData.length > 0 ? (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50/60 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11.5px] font-semibold uppercase tracking-[0.14em] text-red-700">
              <BugIcon className="h-3 w-3" />
              Bug Analysis
            </div>
            <div className="text-[12px] text-slate-700">
              <span className="font-semibold">{message.retrievedData.length}</span> matching bug(s)
            </div>
          </div>
        ) : null}

        {message.intent === "screenshot_analysis" ? (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11.5px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
              <ImageIcon className="h-3 w-3" />
              Screenshot Analysis
            </div>
            <div className="text-[12px] text-slate-700">
              <span className="font-semibold">{screenshotPaths.length || message.retrievedData.length}</span> artifact(s) found
            </div>
            {screenshotPaths.length > 0 ? (
              <div className="mt-2 space-y-1">
                {screenshotPaths.map((path) => (
                  <div key={path} className="truncate rounded-md border border-emerald-200 bg-white px-2 py-1 font-mono text-[10.5px] text-slate-600">
                    {path}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {message.intent === "memory_update" ? (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11.5px] font-medium text-emerald-700">
            <Save className="h-3 w-3" />
            Memory saved · {new Date(message.timestamp).toLocaleString()}
          </div>
        ) : null}

        {isLastInGroup ? (
          <div className="mt-2.5 flex items-center gap-0.5">
            <MessageAction onClick={handleCopy} active={copied} title="Copy">
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            </MessageAction>
            {onRegenerate ? (
              <MessageAction onClick={onRegenerate} title="Regenerate">
                <RefreshCw className="h-3 w-3" />
              </MessageAction>
            ) : null}
            <MessageAction title="Helpful">
              <ThumbsUp className="h-3 w-3" />
            </MessageAction>
            <MessageAction title="Not helpful">
              <ThumbsDown className="h-3 w-3" />
            </MessageAction>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MessageAction({
  children,
  onClick,
  title,
  active = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  title: string;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700",
        active && "bg-emerald-50 text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700",
      )}
    >
      {children}
    </button>
  );
}
