"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { usePathname } from "next/navigation";

export function ClientShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsAuthenticated(!!token);
  }, [pathname]);

  const isAuthRoute = pathname === "/login" || pathname === "/signup" || (pathname === "/" && isAuthenticated === false);

  if (isAuthRoute) {
    return <>{children}</>;
  }

  // Prevent flashing the sidebar on "/" before auth is resolved
  if (pathname === "/" && isAuthenticated === null) {
    return <div className="min-h-screen bg-white"></div>;
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
