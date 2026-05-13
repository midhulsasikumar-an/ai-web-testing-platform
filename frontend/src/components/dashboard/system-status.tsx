"use client";

import { useState, useEffect } from "react";
import { getHealthStatus } from "@/services/auth-api";

interface HealthState {
  status: "checking" | "connected" | "disconnected";
  label: string;
}

export function SystemStatus({ collapsed }: { collapsed: boolean }) {
  const [health, setHealth] = useState<HealthState>({
    status: "checking",
    label: "Checking…",
  });

  useEffect(() => {
    let mounted = true;

    async function check() {
      try {
        const data = await getHealthStatus();
        if (!mounted) return;

        if (data.status === "healthy" && data.mongodb === "connected") {
          setHealth({ status: "connected", label: "MongoDB Connected" });
        } else {
          setHealth({ status: "disconnected", label: "MongoDB Offline" });
        }
      } catch {
        if (!mounted) return;
        setHealth({ status: "disconnected", label: "Backend Offline" });
      }
    }

    check();
    const interval = setInterval(check, 30000); // poll every 30s

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const dotClass =
    health.status === "connected"
      ? "status-dot status-dot-connected"
      : health.status === "disconnected"
      ? "status-dot status-dot-disconnected"
      : "status-dot status-dot-checking";

  return (
    <div className="flex items-center gap-2.5 px-3 py-1.5">
      <div className={dotClass} />
      {!collapsed && (
        <span className="text-[0.65rem] text-sidebar-foreground/50 truncate">
          {health.label}
        </span>
      )}
    </div>
  );
}
