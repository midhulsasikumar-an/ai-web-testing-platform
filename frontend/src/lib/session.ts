export type SessionInfo = {
  userId: string;
  email: string;
  role: string;
  issuedAt: Date | null;
  expiresAt: Date | null;
};

type JwtPayload = {
  sub?: string;
  id?: string;
  user_id?: string;
  email?: string;
  name?: string;
  role?: string;
  iat?: number;
  exp?: number;
};

export function decodeSession(token: string | null | undefined): SessionInfo | null {
  if (!token) return null;

  const parts = token.split(".");
  if (parts.length < 2) return null;

  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
    const json = atob(`${normalized}${padding}`);
    const payload = JSON.parse(json) as JwtPayload;

    return {
      userId: String(payload.id || payload.user_id || payload.sub || "").trim(),
      email: String(payload.email || "").trim(),
      role: String(payload.role || "user").trim(),
      issuedAt: typeof payload.iat === "number" ? new Date(payload.iat * 1000) : null,
      expiresAt: typeof payload.exp === "number" ? new Date(payload.exp * 1000) : null,
    };
  } catch {
    return null;
  }
}

export function formatRelativeTime(date: Date | null): string {
  if (!date) return "—";
  const diffMs = date.getTime() - Date.now();
  const absMs = Math.abs(diffMs);
  const minutes = Math.round(absMs / 60_000);
  const hours = Math.round(absMs / 3_600_000);
  const days = Math.round(absMs / 86_400_000);

  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (minutes < 1) return diffMs >= 0 ? "in a moment" : "just now";
  if (minutes < 60) return formatter.format(diffMs >= 0 ? minutes : -minutes, "minute");
  if (hours < 24) return formatter.format(diffMs >= 0 ? hours : -hours, "hour");
  return formatter.format(diffMs >= 0 ? days : -days, "day");
}

export function formatDateTime(date: Date | null): string {
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function detectBrowser(ua: string): { name: string; os: string } {
  const lower = ua.toLowerCase();
  const name =
    lower.includes("edg/")
      ? "Microsoft Edge"
      : lower.includes("chrome/")
        ? "Chrome"
        : lower.includes("safari/")
          ? "Safari"
          : lower.includes("firefox/")
            ? "Firefox"
            : "Unknown browser";
  const os = lower.includes("win") ? "Windows" : lower.includes("mac") ? "macOS" : lower.includes("linux") ? "Linux" : "Unknown OS";
  return { name, os };
}
