import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ClientShell } from "@/components/layout/client-shell";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "TestPulse AI",
    template: "%s | TestPulse AI",
  },
  description:
    "AI-powered web testing platform. Run automated browser probes, track bugs, and monitor system health with TestPulse AI.",
  applicationName: "TestPulse AI",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/testpulse-ai-logo.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/testpulse-ai-logo.png", type: "image/png", sizes: "512x512" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
