"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TerminalWindow } from "@/components/auth/terminal-window";
import { LogIn } from "lucide-react";
import { useAuth } from "@/context/auth-context";

export function LandingLogin() {
  const router = useRouter();
  const { login, initWarning, clearInitWarning } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-white text-gray-900 relative overflow-hidden">
      {/* Dotted background pattern */}
      <div 
        className="absolute inset-0 pointer-events-none z-0" 
        style={{
          backgroundImage: 'radial-gradient(#e5e7eb 1px, transparent 1px)',
          backgroundSize: '24px 24px'
        }}
      />

      {/* Navbar */}
      <header className="relative z-10 flex flex-col sm:flex-row items-center justify-between px-8 py-6 gap-4">
        <Link href="/" className="text-xl font-bold text-blue-600">
          TestPulse AI
        </Link>
        <div className="text-sm">
          <span className="text-gray-600 mr-4">Don&apos;t have an account?</span>
          <Link href="/signup" className="font-semibold text-blue-600 hover:text-blue-700">
            Sign up
          </Link>
        </div>
      </header>

      {/* Main Content Split */}
      {/* Stored-session warning banner when backend was unreachable during init */}
      {initWarning && (
        <div className="relative z-10 mx-auto max-w-7xl w-full px-6 lg:px-12 pt-4">
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <span className="mt-0.5 shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </span>
            <p className="flex-1">{initWarning.message}</p>
            <button
              onClick={clearInitWarning}
              className="shrink-0 rounded p-0.5 text-amber-600 hover:text-amber-900 transition-colors"
              aria-label="Dismiss"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
      )}

      <main className="flex-1 flex flex-col lg:flex-row items-center max-w-7xl mx-auto w-full p-6 lg:p-12 gap-12 relative z-10">
        
        {/* Left Side: Copy & Benefits */}
        <div className="flex-1 space-y-8 relative">
          {/* Faint code watermark */}
          <div className="absolute -top-20 -left-20 text-gray-100/50 font-mono text-2xl rotate-[-15deg] pointer-events-none whitespace-pre select-none -z-10 hidden md:block">
{`async function testPulse() {
  const heart = await monitor.status();
  if (heart.beat === 0) {
    throw new Error("Pulse lost");
  }
}`}
          </div>

          <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-gray-900 leading-tight max-w-md">
            Precision-engineered for the modern developer.
          </h1>
          
        </div>

        {/* Right Side: Terminal Form (Login Form) */}
        <div className="flex-1 w-full max-w-[500px] relative">
          {/* Subtle glow behind terminal */}
          <div className="absolute inset-0 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />

          <TerminalWindow title="login.config.ts">
            <div className="space-y-5">
              {/* Comment */}
              <p className="text-[#32CD32]/80">{"// Enter your credentials to access your terminal"}</p>

              <form onSubmit={handleLogin} className="space-y-5">
                {/* Email Field */}
                <div className="space-y-2">
                  <div className="flex text-sm">
                    <span className="text-[#32CD32]">email:</span>
                      <span className="text-[#00f2fe] ml-2">&quot;developer@host.io&quot;</span>
                  </div>
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="dev@testpulse.ai"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-transparent border border-[#444] rounded px-4 py-3 text-gray-300 font-mono text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-[#555]"
                    required
                  />
                </div>

                {/* Password Field */}
                <div className="space-y-2">
                  <div className="flex text-sm">
                    <span className="text-[#32CD32]">password:</span>
                    <span className="text-[#00f2fe] ml-2">&quot;********&quot;</span>
                  </div>
                  <input
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-transparent border border-[#444] rounded px-4 py-3 text-gray-300 font-mono text-sm tracking-[0.2em] focus:outline-none focus:border-blue-500 transition-colors placeholder:text-[#555] placeholder:tracking-normal"
                    required
                  />
                </div>
                
                {error && <div className="text-red-500 text-sm mt-2 font-sans">{error}</div>}

                {/* Login Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#2f80ed] hover:bg-blue-700 disabled:opacity-50 text-white font-sans font-medium py-3 rounded flex items-center justify-center gap-2 transition-colors mt-6"
                >
                  {loading ? "Logging In..." : "Log In"}
                  <LogIn size={18} className="rotate-180" />
                </button>
              </form>

              {/* Forgot password text */}
              <div className="text-center pt-2">
                <p className="text-[#ff3b30] text-xs font-mono">
                  auth.requestPasswordReset()
                </p>
              </div>
            </div>
          </TerminalWindow>
          
          {/* Trusted by block */}
          <div className="mt-8 flex items-center justify-center gap-3 opacity-60">
            <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center border border-gray-200">
              <div className="w-3 h-3 border-2 border-gray-400 rounded-[2px]" />
            </div>
            <span className="text-xs font-mono font-semibold tracking-widest text-gray-500 uppercase">
              Trusted by 1000+ Repos
            </span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 flex flex-col md:flex-row items-center justify-between px-8 py-8 text-sm text-gray-500 bg-white/80 backdrop-blur-sm mt-auto gap-4">
        <div className="font-bold text-gray-900 text-lg">TestPulse AI</div>
        <div className="text-center flex-1">
          © 2024 TestPulse AI. Built for technical precision and human warmth.
        </div>
        <div className="flex items-center gap-6">
          <Link href="/privacy" className="hover:text-gray-900">Privacy</Link>
          <Link href="/terms" className="hover:text-gray-900">Terms</Link>
          <Link href="/support" className="hover:text-gray-900">Support</Link>
        </div>
      </footer>
    </div>
  );
}
