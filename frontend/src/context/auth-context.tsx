"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getCurrentUser, loginWithBackend, signupWithBackend } from "@/services/auth-api";
import { clearAuthSession, getStoredAuthSession, storeAuthSession, type AuthSession } from "@/services/http";

export interface User {
  id: string;
  name: string;
  email: string;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isReady: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function toUser(session: AuthSession | null): User | null {
  if (!session) return null;
  return {
    id: session.user.id,
    name: session.user.name,
    email: session.user.email,
    role: session.user.role,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const hydrated = getStoredAuthSession();
        if (hydrated?.token) {
          const currentUser = await getCurrentUser(hydrated.token);
          const restored: AuthSession = {
            token: hydrated.token,
            user: {
              id: currentUser.id,
              name: currentUser.name,
              email: currentUser.email,
              role: currentUser.role,
            },
          };
          storeAuthSession(restored);
          if (active) setSession(restored);
          return;
        }
      } catch (error) {
        console.error("Failed to initialize auth session", error);
        clearAuthSession();
        if (active) setSession(null);
      } finally {
        if (active) setIsReady(true);
      }
    }

    init();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      const nextSession = await loginWithBackend(email, password);
      storeAuthSession(nextSession);
      setSession(nextSession);
      return true;
    } catch (error) {
      console.error("Login failed", error);
      return false;
    }
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string): Promise<boolean> => {
    try {
      const nextSession = await signupWithBackend(name, email, password);
      storeAuthSession(nextSession);
      setSession(nextSession);
      return true;
    } catch (error) {
      console.error("Signup failed", error);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    clearAuthSession();
    setSession(null);
  }, []);

  const user = toUser(session);

  return (
    <AuthContext.Provider
      value={{
        user,
        token: session?.token ?? null,
        isAuthenticated: !!session?.token,
        isReady,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}