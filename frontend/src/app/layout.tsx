import type { Metadata } from "next";
import "./globals.css";
import { ClientShell } from "@/components/layout/client-shell";

export const metadata: Metadata = {
  title: "SignalTrack — AI Bug Tracking Dashboard",
  description:
    "AI-powered testing and bug tracking platform. Run automated probes, track bugs, and monitor system health with the Precision QA System.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
