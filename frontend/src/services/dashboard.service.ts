import { apiFetch } from "./api";
import { DashboardStats } from "@/types";

export const dashboardService = {
  getStats: () => 
    apiFetch("/api/dashboard/stats", {
      method: "GET",
    }) as Promise<DashboardStats>,
};
