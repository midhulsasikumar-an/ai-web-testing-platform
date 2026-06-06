// ── Centralized date/time/duration formatting ─────────────────────

/**
 * Format an ISO date string to a short human-readable date.
 * e.g. "Apr 28, 2026"
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format an ISO date string to a long human-readable date.
 * e.g. "Mon, Apr 28, 2026"
 */
export function formatDateLong(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format an ISO date string to a 12-hour time string.
 * e.g. "10:30 AM"
 */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Format an ISO date string to a 24-hour time string with seconds.
 * e.g. "10:30:12"
 */
export function formatTime24(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format a duration in milliseconds to a human-readable string.
 * e.g. "3.4s"
 */
export function formatDuration(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}
