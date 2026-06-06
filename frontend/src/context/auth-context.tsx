"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import {
  loginUser,
  signupUser,
  getCurrentUser,
} from "@/services/auth-api";

// ── Types ──────────────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "signaltrack_token";

// ── Provider ───────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Hydrate session from stored JWT on mount
  useEffect(() => {
    async function hydrate() {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const { user: userData } = await getCurrentUser(token);
        setUser({
          id: userData.id,
          name: userData.name,
          email: userData.email,
        });
      } catch {
        // Token expired or invalid — clear it
        localStorage.removeItem(TOKEN_KEY);
      } finally {
        setIsLoading(false);
      }
    }

    hydrate();
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setError(null);
    try {
      const { token, user: userData } = await loginUser(email, password);
      localStorage.setItem(TOKEN_KEY, token);
      setUser({
        id: userData.id,
        name: userData.name,
        email: userData.email,
      });
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      return false;
    }
  }, []);

  const signup = useCallback(
    async (name: string, email: string, password: string): Promise<boolean> => {
      setError(null);
      try {
        const { token, user: userData } = await signupUser(name, email, password);
        localStorage.setItem(TOKEN_KEY, token);
        setUser({
          id: userData.id,
          name: userData.name,
          email: userData.email,
        });
        return true;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Signup failed";
        setError(message);
        return false;
      }
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        signup,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
