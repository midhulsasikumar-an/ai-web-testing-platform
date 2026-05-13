"use client";

import { AuthProvider, useAuth } from "@/context/auth-context";
import { BugProvider } from "@/context/bug-context";
import { Sidebar } from "@/components/layout/sidebar";
import LoginPage from "@/app/login/page";

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  // Loading spinner during JWT hydration
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0a0a1a]">
        <div className="flex flex-col items-center gap-4">
          <div className="auth-orbital-spinner">
            <div className="orbital-ring" />
            <div className="orbital-ring" style={{ animationDelay: "-0.4s", width: 36, height: 36 }} />
            <div className="orbital-core" />
          </div>
          <p className="text-sm text-white/40 font-medium tracking-wide">Initializing…</p>
        </div>
      </div>
    );
  }

  // Not logged in → show login page
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Authenticated → show the app
  return (
    <BugProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </BugProvider>
  );
}

export function ClientShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AuthGate>{children}</AuthGate>
    </AuthProvider>
  );
}
