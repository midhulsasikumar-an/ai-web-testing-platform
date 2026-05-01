"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

// ── Types ──────────────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => boolean;
  signup: (name: string, email: string, password: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── Dummy user store ───────────────────────────────────────────────

interface StoredUser extends User {
  password: string;
}

const defaultUsers: StoredUser[] = [
  { id: "usr-001", name: "Demo User", email: "demo@bugtracker.io", password: "demo123" },
];

// ── Provider ───────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<StoredUser[]>(defaultUsers);

  const login = useCallback(
    (email: string, password: string): boolean => {
      const found = users.find(
        (u) => u.email.toLowerCase() === email.toLowerCase() && u.password === password
      );
      if (found) {
        setUser({ id: found.id, name: found.name, email: found.email });
        return true;
      }
      return false;
    },
    [users]
  );

  const signup = useCallback(
    (name: string, email: string, password: string): boolean => {
      const exists = users.some((u) => u.email.toLowerCase() === email.toLowerCase());
      if (exists) return false;

      const newUser: StoredUser = {
        id: `usr-${Date.now().toString(36)}`,
        name,
        email,
        password,
      };
      setUsers((prev) => [...prev, newUser]);
      setUser({ id: newUser.id, name: newUser.name, email: newUser.email });
      return true;
    },
    [users]
  );

  const logout = useCallback(() => setUser(null), []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, logout }}>
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
