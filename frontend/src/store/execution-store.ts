import { create } from "zustand";
import type { WorkflowState, StreamLogLine } from "@/types";

interface ExecutionState {
  executionId: string | null;
  status: WorkflowState | null;
  logs: StreamLogLine[];
  url: string | null;
  progress: number;
  
  // Actions
  startExecution: (id: string, url: string) => void;
  updateStatus: (status: WorkflowState) => void;
  addLog: (log: StreamLogLine) => void;
  setProgress: (progress: number) => void;
  reset: () => void;
}

export const useExecutionStore = create<ExecutionState>((set) => ({
  executionId: null,
  status: null,
  logs: [],
  url: null,
  progress: 0,

  startExecution: (id, url) => set({ executionId: id, url, status: "queued", logs: [], progress: 0 }),
  updateStatus: (status) => set({ status }),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  setProgress: (progress) => set({ progress }),
  reset: () => set({ executionId: null, status: null, logs: [], url: null, progress: 0 })
}));
