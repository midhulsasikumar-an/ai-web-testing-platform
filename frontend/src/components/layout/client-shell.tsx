"use client";

import { BugProvider } from "@/context/bug-context";
import { Sidebar } from "@/components/layout/sidebar";

export function ClientShell({ children }: { children: React.ReactNode }) {
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
