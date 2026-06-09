"use client";

import { AuthProvider } from "@/context/auth-context";
import { BugProvider } from "@/context/bug-context";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";
import { AppHeader } from "@/components/layout/app-header";
import { useAuth } from "@/context/auth-context";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

function AppGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isReady } = useAuth();

  const publicRoutes = new Set(["/", "/login", "/signup", "/privacy", "/terms", "/support"]);
  const isPublicRoute = publicRoutes.has(pathname);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isReady) return;

    if (!isAuthenticated && !isPublicRoute) {
      router.replace("/login");
      return;
    }

  }, [isAuthenticated, isPublicRoute, isReady, router]);

  if (!isReady) {
    return (
      <div className="grid min-h-screen place-items-center bg-[var(--shell-bg)] text-sm text-slate-500">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
          Loading session…
        </div>
      </div>
    );
  }

  if (isPublicRoute) {
    return <>{children}</>;
  }

  return (
    <div className="shell-bg flex min-h-screen text-slate-900">
      {/* Desktop sidebar is fixed so the page never scrolls beneath it. */}
      <div className="fixed inset-y-0 left-0 z-30 hidden lg:block">
        <Sidebar />
      </div>

      <MobileNav open={mobileNavOpen} onOpenChange={setMobileNavOpen} />

      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <AppHeader
          showMobileMenuButton
          onOpenMobileNav={() => setMobileNavOpen(true)}
        />
        <main className="flex-1">
          <div className="mx-auto w-full max-w-[1400px] px-4 pb-10 pt-5 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
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
