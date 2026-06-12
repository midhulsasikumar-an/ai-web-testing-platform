"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { AuthApiError, getCurrentUser, loginWithBackend, logoutWithBackend, signupWithBackend, toAuthErrorMessage } from "@/services/auth-api";
import {
  clearAuthToken,
  clearRefreshToken,
  getStoredAuthToken,
  getStoredAuthUser,
  onAuthTokenCleared,
  storeAuthToken,
  storeAuthUser,
  storeRefreshToken,
} from "@/services/http";

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
  refreshUser: () => Promise<void>;
  clearInitWarning: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthSession = {
  token: string;
  user: User;
};

function toUser(session: AuthSession | null): User | null {
  return session ? session.user : null;
}

function decodeJwtFallbackUser(token: string): User | null {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) {
      return null;
    }

    const normalized = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
    const payloadJson = atob(`${normalized}${padding}`);
    const payload = JSON.parse(payloadJson) as Record<string, unknown>;
    const expiresAt = typeof payload.exp === "number" ? payload.exp * 1000 : null;
    if (expiresAt && expiresAt <= Date.now()) {
      return null;
    }

    const id = String(payload.id || payload.user_id || payload.sub || "").trim();
    const email = String(payload.email || "").trim();
    const name = String(payload.name || email || id || "").trim();
    if (!id || !email) {
      return null;
    }

    return {
      id,
      name,
      email,
      role: String(payload.role || "user"),
    };
  } catch {
    return null;
  }
}

function restoreStoredSession(): AuthSession | null {
  const token = getStoredAuthToken();
  if (!token) return null;

  const storedUser = getStoredAuthUser<User>();
  if (storedUser?.id && storedUser.email) {
    return { token, user: storedUser };
  }

  const fallbackUser = decodeJwtFallbackUser(token);
  return fallbackUser ? { token, user: fallbackUser } : null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [initWarning, setInitWarning] = useState<InitWarning | null>(null);

  useEffect(() => {
    let active = true;

    async function init() {
      const restoredSession = restoreStoredSession();

      if (!restoredSession) {
        if (active) {
          setSession(null);
          setIsReady(true);
        }
        return;
      }

      setSession(restoredSession);

      try {
        const token = restoredSession.token;
        const currentUser = await getCurrentUser(token);
        const restored: AuthSession = { token, user: currentUser };
        storeAuthToken(token);
        storeAuthUser(currentUser);

        if (active) {
          setSession(restored);
          setInitWarning(null);
        }
      } catch (error) {
        if (error instanceof AuthApiError) {
          switch (error.code) {
            case "UNAUTHORIZED":
              if (active) {
                clearRefreshToken();
                clearAuthToken();
                setSession(null);
                setInitWarning({
                  code: "BACKEND_UNAVAILABLE",
                  message: "Saved session has expired or is invalid. Please sign in again.",
                });
              }
              break;

            case "BACKEND_UNAVAILABLE":
            case "NETWORK_ERROR":
              if (active) {
                setInitWarning({
                  code: error.code as InitWarning["code"],
                  message: error.message,
                });
              }
              break;

            case "SERVER_ERROR":
              if (active) {
                setInitWarning({
                  code: "BACKEND_UNAVAILABLE",
                  message: error.message,
                });
              }
              break;

            case "TIMEOUT":
              if (active) {
                setInitWarning({
                  code: "TIMEOUT",
                  message: error.message,
                });
              }
              break;

            default:
              if (active) {
                setInitWarning({
                  code: "BACKEND_UNAVAILABLE",
                  message: "Saved session could not be validated. Sign in again if protected actions fail.",
                });
              }
              break;
          }
        } else {
          if (active) {
            setInitWarning({
              code: "BACKEND_UNAVAILABLE",
              message: "Saved session could not be validated. Sign in again if protected actions fail.",
            });
          }
        }
      } finally {
        if (active) setIsReady(true);
      }
    }

    init();

    const removeAuthListener = onAuthTokenCleared(() => {
      if (active) {
        setSession(null);
        setInitWarning(null);
      }
    });

    const handleStorage = (event: StorageEvent) => {
      if (event.key === "auth_token" && !event.newValue && active) {
        setSession(null);
        setInitWarning(null);
      }
    };

    window.addEventListener("storage", handleStorage);

    return () => {
      active = false;
      removeAuthListener();
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    try {
      const nextSession = await loginWithBackend(email, password);
      storeAuthToken(nextSession.token);
      storeAuthUser(nextSession.user);
      if (nextSession.refreshToken) {
        storeRefreshToken(nextSession.refreshToken);
      }
      setSession(nextSession);
      setInitWarning(null);
    } catch (error) {
      throw new Error(toAuthErrorMessage(error));
    }
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string): Promise<void> => {
    try {
      const nextSession = await signupWithBackend(name, email, password);
      storeAuthToken(nextSession.token);
      storeAuthUser(nextSession.user);
      if (nextSession.refreshToken) {
        storeRefreshToken(nextSession.refreshToken);
      }
      setSession(nextSession);
      setInitWarning(null);
    } catch (error) {
      throw new Error(toAuthErrorMessage(error));
    }
  }, []);

  const logout = useCallback(() => {
    const token = session?.token ?? getStoredAuthToken();
    if (token) {
      void logoutWithBackend(token).catch(() => undefined);
    }
    clearRefreshToken();
    clearAuthToken();
    setSession(null);
    setInitWarning(null);
  }, [session?.token]);

  const refreshUser = useCallback(async (): Promise<void> => {
    const token = getStoredAuthToken();
    if (!token) {
      setSession(null);
      return;
    }
    const currentUser = await getCurrentUser(token);
    storeAuthUser(currentUser);
    setSession({ token, user: currentUser });
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
        refreshUser,
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
