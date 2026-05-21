"use client";

import { AuthProvider } from "@/context/auth-context";
import { BugProvider } from "@/context/bug-context";
import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/context/auth-context";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

function AppGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isReady } = useAuth();

  const publicRoutes = new Set(["/", "/login", "/signup"]);
  const isPublicRoute = publicRoutes.has(pathname);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    if (!isAuthenticated && !isPublicRoute) {
      router.replace("/login");
      return;
    }

    if (isAuthenticated && isPublicRoute) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isPublicRoute, isReady, router]);

  if (!isReady) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading session...</div>;
  }

  if (isPublicRoute) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
          {children}
        </div>
      </main>
    </div>
  );
}

export function ClientShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <BugProvider>
        <AppGuard>{children}</AppGuard>
      </BugProvider>
    </AuthProvider>
  );
}
