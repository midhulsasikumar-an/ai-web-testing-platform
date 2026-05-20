import { create } from "zustand";
import { TestResult, AIFinding } from "@/types";
import { executionService } from "@/services/execution.service";

interface TestHistoryState {
  testResults: TestResult[];
  aiFindings: AIFinding[];
  loading: boolean;
  error: string | null;
  fetchHistory: () => Promise<void>;
  addTestResult: (result: TestResult) => void;
}

export const useTestHistoryStore = create<TestHistoryState>((set, get) => ({
  testResults: [], // Remove mock data, let API populate this
  aiFindings: [],
  loading: false,
  error: null,
  
  fetchHistory: async () => {
    set({ loading: true, error: null });
    try {
      // In a real app, we'd have a testHistoryService or executionService.getHistory()
      // const results = await executionService.getHistory();
      // set({ testResults: results, loading: false });
      
      // For now, since backend API might not have this yet, we just set empty
      set({ loading: false }); 
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  addTestResult: (result) => {
    set((state) => ({ testResults: [result, ...state.testResults] }));
  }
}));
