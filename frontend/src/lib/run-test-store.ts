"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AIPlanResponse, TestApiResponse } from "@/services/test-api";

const STORAGE_KEY = "run_test_workspace_v1";

export type ChatMessage = {
  id: string;
  from: "user" | "ai";
  text: string;
  timestamp: number;
};

export type RunWorkspaceState = {
  targetUrl: string;
  testName: string;
  testType: string;
  browser: string;
  device: string;
  coverageLevel: string;
  executionSettings: Record<string, unknown> | null;

  testId: string | null;
  testData: TestApiResponse | null;
  running: boolean;

  aiPlan: AIPlanResponse | null;
  planSuppressed: boolean;
  planExpanded: boolean;

  chatMessages: ChatMessage[];
  chatInput: string;
  lastInstruction: string;
  initialInstruction: string;

  followTimeline: boolean;
  aiPanelOpen: boolean;
};

export const INITIAL_WORKSPACE_STATE: RunWorkspaceState = {
  targetUrl: "",
  testName: "",
  testType: "e2e",
  browser: "",
  device: "",
  coverageLevel: "fast",
  executionSettings: {
    max_scenarios: 2,
    scenario_timeout_seconds: 45,
    step_timeout_seconds: 15,
  },
  testId: null,
  testData: null,
  running: false,
  aiPlan: null,
  planSuppressed: false,
  planExpanded: true,
  chatMessages: [],
  chatInput: "",
  lastInstruction: "",
  initialInstruction: "",
  followTimeline: true,
  aiPanelOpen: false,
};

function isBrowser() {
  return typeof window !== "undefined";
}

function readStorage(): RunWorkspaceState {
  if (!isBrowser()) return INITIAL_WORKSPACE_STATE;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return INITIAL_WORKSPACE_STATE;
    const parsed = JSON.parse(raw) as Partial<RunWorkspaceState>;
    return {
      ...INITIAL_WORKSPACE_STATE,
      ...parsed,
      // Always start not-running on hydration; the page will detect any
      // pending execution and resume polling, but the spinner state is
      // only true while a fetch is actually in flight.
      running: false,
      // Reset transient UI panels so reopening doesn't auto-open a drawer.
      aiPanelOpen: false,
      followTimeline: parsed.followTimeline ?? true,
    };
  } catch {
    return INITIAL_WORKSPACE_STATE;
  }
}

function writeStorage(state: RunWorkspaceState) {
  if (!isBrowser()) return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Quota or serialization error – ignore; UI still works in memory.
  }
}

export function clearRunTestStorage() {
  if (!isBrowser()) return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function useRunWorkspace() {
  const [state, setState] = useState<RunWorkspaceState>(INITIAL_WORKSPACE_STATE);
  const [hydrated, setHydrated] = useState(false);
  const hasHydratedRef = useRef(false);

  useEffect(() => {
    // Storage hydration runs once on mount; mirroring external state into
    // React is the intent of this effect, which the rule does not model.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(readStorage());
    setHydrated(true);
    hasHydratedRef.current = true;
  }, []);

  useEffect(() => {
    if (!hasHydratedRef.current) return;
    writeStorage(state);
  }, [state]);

  const update = useCallback(
    (patch: Partial<RunWorkspaceState> | ((prev: RunWorkspaceState) => Partial<RunWorkspaceState>)) => {
      setState((prev) => {
        const next = typeof patch === "function" ? patch(prev) : patch;
        return { ...prev, ...next };
      });
    },
    []
  );

  const reset = useCallback(() => {
    clearRunTestStorage();
    setState(INITIAL_WORKSPACE_STATE);
  }, []);

  const setChatInput = useCallback((value: string) => {
    setState((prev) => ({ ...prev, chatInput: value }));
  }, []);

  const appendChat = useCallback((message: ChatMessage) => {
    setState((prev) => ({ ...prev, chatMessages: [...prev.chatMessages, message] }));
  }, []);

  const resetChat = useCallback(() => {
    setState((prev) => ({
      ...prev,
      chatMessages: [],
      chatInput: "",
      lastInstruction: "",
    }));
  }, []);

  const setExecutionStatusMessage = useCallback((status: string) => {
    const text = `Execution status: ${status}`;
    setState((prev) => {
      const msgs = prev.chatMessages;
      for (let i = msgs.length - 1; i >= 0; i -= 1) {
        const m = msgs[i];
        if (m.from === "ai" && m.text.startsWith("Execution status:")) {
          if (m.text === text) return prev;
          const next = msgs.slice();
          next[i] = { ...m, text, timestamp: Date.now() };
          return { ...prev, chatMessages: next };
        }
      }
      return {
        ...prev,
        chatMessages: [
          ...msgs,
          {
            id: `status-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            from: "ai",
            text,
            timestamp: Date.now(),
          },
        ],
      };
    });
  }, []);

  return {
    state,
    update,
    reset,
    hydrated,
    setChatInput,
    appendChat,
    resetChat,
    setExecutionStatusMessage,
  };
}
