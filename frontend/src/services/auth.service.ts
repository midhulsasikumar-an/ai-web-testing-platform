import { apiFetch } from "./api";

export const authService = {
  login: (credentials: any) => 
    apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
    
  signup: (userData: any) => 
    apiFetch("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(userData),
    }),
};
