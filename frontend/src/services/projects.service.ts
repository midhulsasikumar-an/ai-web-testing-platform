import { apiFetch } from "./api";

export const projectsService = {
  getProjects: () => 
    apiFetch("/api/projects", {
      method: "GET",
    }),
};
