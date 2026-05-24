"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { AuthApiError, getCurrentUser, loginWithBackend, signupWithBackend, toAuthErrorMessage } from "@/services/auth-api";
import { clearAuthSession, getStoredAuthSession, storeAuthSession, type AuthSession } from "@/services/http";

export interface User {
  id: string;
  name: string;
  email: string;
  role?: string;
}

export interface InitWarning {
  code: "BACKEND_UNAVAILABLE" | "NETWORK_ERROR" | "TIMEOUT" | "ENDPOINT_NOT_FOUND";
  message: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isReady: boolean;
  initWarning: InitWarning | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  clearInitWarning: () => void;
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
  const [initWarning, setInitWarning] = useState<InitWarning | null>(null);

  useEffect(() => {
    let active = true;

    async function init() {
      const hydrated = getStoredAuthSession();

      // ── Case 1: No token in storage ──────────────────────────────────
      if (!hydrated?.token) {
        console.info("[auth] No stored session found. Starting as unauthenticated.");
        if (active) {
          setSession(null);
          setIsReady(true);
        }
        return;
      }

      // ── Case 2: Token exists — validate it against backend ────────────
      console.info("[auth] Stored session token found. Validating...");

      try {
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

        if (active) {
          setSession(restored);
          setInitWarning(null);
          console.info("[auth] Session validated successfully.");
        }
      } catch (error) {
        if (error instanceof AuthApiError) {
          switch (error.code) {
            // ── Token invalid / expired — clear it ──────────────────────
            case "UNAUTHORIZED":
              console.info("[auth] Token expired or invalid. Clearing session.");
              clearAuthSession();
              if (active) {
                setSession(null);
                setInitWarning(null);
              }
              break;

            // ── Backend not reachable — keep token, degrade gracefully ──
            case "BACKEND_UNAVAILABLE":
            case "NETWORK_ERROR":
            case "ENDPOINT_NOT_FOUND":
              console.warn("[auth] Backend unreachable during init. Keeping stored token for next attempt.",
                { code: error.code, message: error.message }
              );
              if (active) {
                setSession(null);
                setInitWarning({
                  code: error.code as InitWarning["code"],
                  message: error.message,
                });
              }
              break;

            // ── Request timed out — keep token, degrade gracefully ──────
            case "TIMEOUT":
              console.warn("[auth] Session validation timed out. Keeping stored token for next attempt.",
                { code: error.code, message: error.message }
              );
              if (active) {
                setSession(null);
                setInitWarning({
                  code: "TIMEOUT",
                  message: error.message,
                });
              }
              break;

            // ── Server error or unexpected failure — clear to be safe ────
            default:
              console.error("[auth] Unexpected AuthApiError during init. Clearing session.",
                { code: error.code, message: error.message }
              );
              clearAuthSession();
              if (active) {
                setSession(null);
                setInitWarning(null);
              }
              break;
          }
        } else {
          // Non-AuthApiError (shouldn't happen, but be safe)
          console.error("[auth] Non-auth error during session init. Clearing session.", error);
          clearAuthSession();
          if (active) {
            setSession(null);
            setInitWarning(null);
          }
        }
      } finally {
        if (active) setIsReady(true);
      }
    }

    init();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    try {
      const nextSession = await loginWithBackend(email, password);
      storeAuthSession(nextSession);
      setSession(nextSession);
      setInitWarning(null);
    } catch (error) {
      console.error("Login failed", error);
      throw new Error(toAuthErrorMessage(error));
    }
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string): Promise<void> => {
    try {
      const nextSession = await signupWithBackend(name, email, password);
      storeAuthSession(nextSession);
      setSession(nextSession);
      setInitWarning(null);
    } catch (error) {
      console.error("Signup failed", error);
      throw new Error(toAuthErrorMessage(error));
    }
  }, []);

  const logout = useCallback(() => {
    clearAuthSession();
    setSession(null);
    setInitWarning(null);
  }, []);

  const clearInitWarning = useCallback(() => {
    setInitWarning(null);
  }, []);

  const user = toUser(session);

  return (
    <AuthContext.Provider
      value={{
        user,
        token: session?.token ?? null,
        isAuthenticated: !!session?.token,
        isReady,
        initWarning,
        login,
        signup,
        logout,
        clearInitWarning,
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