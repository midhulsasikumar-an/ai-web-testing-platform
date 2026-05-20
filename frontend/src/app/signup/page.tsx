"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TerminalWindow } from "@/components/auth/terminal-window";
import { UserPlus } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: fullName, email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Signup failed");
      }

      localStorage.setItem("token", data.access_token);
      router.push("/"); // Redirect to dashboard
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-white text-gray-900 relative">
      {/* Dotted background pattern */}
      <div 
        className="absolute inset-0 pointer-events-none z-0" 
        style={{
          backgroundImage: 'radial-gradient(#e5e7eb 1px, transparent 1px)',
          backgroundSize: '24px 24px'
        }}
      />

      {/* Navbar */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <Link href="/" className="text-xl font-bold text-blue-600">
          TestPulse AI
        </Link>
        <nav className="flex items-center gap-8 text-sm text-gray-600 hidden md:flex">
          <Link href="#" className="hover:text-gray-900">Docs</Link>
          <Link href="#" className="hover:text-gray-900">API</Link>
          <Link href="#" className="hover:text-gray-900">Pricing</Link>
          <Link href="/" className="hover:text-gray-900">Login</Link>
          <Link href="/signup" className="font-semibold text-blue-600 border-b-2 border-blue-600 pb-1">Sign Up</Link>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6 relative z-10">
        <div className="w-full max-w-[600px] relative">
          {/* Subtle glow behind terminal */}
          <div className="absolute inset-0 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />
          
          <TerminalWindow title="signup.config.ts">
            <div className="space-y-6">
              {/* Code comments & imports */}
              <div className="space-y-2">
                <p className="text-gray-500">{"// Initialize your developer profile"}</p>
                <p>
                  <span className="text-cyan-400">import</span>{" "}
                  <span className="text-green-400">register</span>{" "}
                  <span className="text-cyan-400">from</span>{" "}
                  <span className="text-cyan-400">'@testpulse/auth'</span>
                </p>
              </div>

              <form onSubmit={handleSignup} className="space-y-6">
                {/* Full Name Field */}
                <div className="space-y-2">
                  <div className="flex text-sm">
                    <span className="text-green-400">full_name</span>
                    <span className="text-cyan-400 ml-2">"</span>
                  </div>
                  <div className="pl-4">
                    <input
                      type="text"
                      placeholder="e.g. Linus Torvalds"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded px-4 py-3 text-cyan-400 font-mono text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
                      required
                    />
                  </div>
                  <div className="text-cyan-400">"</div>
                </div>

                {/* Email Field */}
                <div className="space-y-2">
                  <div className="flex text-sm">
                    <span className="text-green-400">email</span>
                    <span className="text-cyan-400 ml-2">"</span>
                  </div>
                  <div className="pl-4">
                    <input
                      type="email"
                      placeholder="dev@testpulse.ai"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded px-4 py-3 text-cyan-400 font-mono text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
                      required
                    />
                  </div>
                  <div className="text-cyan-400">"</div>
                </div>

                {/* Password Field */}
                <div className="space-y-2">
                  <div className="flex text-sm">
                    <span className="text-green-400">password</span>
                    <span className="text-cyan-400 ml-2">"</span>
                  </div>
                  <div className="pl-4">
                    <input
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded px-4 py-3 text-cyan-400 font-mono text-sm tracking-[0.2em] focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
                      required
                      minLength={6}
                    />
                  </div>
                  <div className="text-cyan-400">"</div>
                </div>
                
                {error && <div className="text-red-500 text-sm mt-2 font-sans">{error}</div>}

                {/* Create Account Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#0066ff] hover:bg-blue-700 disabled:opacity-50 text-white font-sans font-bold py-3.5 rounded flex items-center justify-center gap-2 transition-colors mt-8"
                >
                  <UserPlus size={18} />
                  {loading ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
                </button>
              </form>

              {/* Login Link */}
              <div className="text-center pt-4 text-sm text-gray-400 font-sans">
                Already have an account?{" "}
                <Link href="/" className="text-cyan-400 hover:underline">
                  Log in
                </Link>
              </div>

              {/* Terms */}
              <div className="pt-8 pb-2">
                <p className="text-gray-500 text-xs italic opacity-80 text-center font-sans">
                  By signing up, you agree to our Terms of Service.
                </p>
              </div>
            </div>
          </TerminalWindow>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 flex flex-col md:flex-row items-center justify-between px-8 py-6 text-sm text-gray-500 bg-white/80 backdrop-blur-sm gap-4">
        <div className="font-bold text-blue-600 text-lg">TestPulse AI</div>
        <div className="flex items-center gap-6">
          <Link href="#" className="hover:text-gray-900">Status</Link>
          <Link href="#" className="hover:text-gray-900">GitHub</Link>
          <Link href="#" className="hover:text-gray-900">Changelog</Link>
          <Link href="#" className="hover:text-gray-900">Privacy</Link>
          <Link href="#" className="hover:text-gray-900">Terms</Link>
        </div>
        <div>© 2024 TestPulse AI. Built for developers.</div>
      </footer>
    </div>
  );
}
