import { create } from "zustand";
import { bugsService } from "@/services/bugs.service";
import { Bug, BugStatus } from "@/types";

interface BugsState {
  bugs: Bug[];
  loading: boolean;
  error: string | null;
  fetchBugs: () => Promise<void>;
  updateBugStatus: (bugId: string, status: BugStatus) => Promise<void>;
}

export const useBugsStore = create<BugsState>((set, get) => ({
  bugs: [],
  loading: false,
  error: null,
  
  fetchBugs: async () => {
    set({ loading: true, error: null });
    try {
      const bugs = await bugsService.getBugs();
      set({ bugs, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  updateBugStatus: async (bugId: string, status: BugStatus) => {
    try {
      const updatedBug = await bugsService.updateBugStatus(bugId, status);
      const { bugs } = get();
      set({ 
        bugs: bugs.map(b => b.id === bugId ? updatedBug : b) 
      });
    } catch (err: any) {
      console.error("Failed to update bug status:", err);
    }
  }
}));
