"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus } from "lucide-react";

import { TerminalWindow } from "@/components/auth/terminal-window";
import { useAuth } from "@/context/auth-context";

export function SignupCard() {
  const router = useRouter();
  const { signup } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signup(name, email, password);
      router.replace("/dashboard");
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white p-6">
      <div className="w-full max-w-xl">
        <TerminalWindow title="signup.config.ts">
          <p className="text-[#32CD32]/80 mb-5">{"// Create your TestPulse account"}</p>
          <form onSubmit={handleSignup} className="space-y-4">
            <input
              type="text"
              autoComplete="name"
              placeholder="Full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-transparent border border-[#444] rounded px-4 py-3 text-gray-300"
              required
            />
            <input
              type="email"
              autoComplete="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-transparent border border-[#444] rounded px-4 py-3 text-gray-300"
              required
            />
            <input
              type="password"
              autoComplete="new-password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-transparent border border-[#444] rounded px-4 py-3 text-gray-300"
              minLength={6}
              required
            />
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#2f80ed] hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-3 rounded flex items-center justify-center gap-2"
            >
              {loading ? "Creating account..." : "Create account"}
              <UserPlus size={18} />
            </button>
          </form>
          <p className="text-xs text-gray-400 mt-5 text-center">
            Already have an account? <Link href="/login" className="text-blue-400 hover:text-blue-300">Log in</Link>
          </p>
        </TerminalWindow>
      </div>
    </div>
  );
}
