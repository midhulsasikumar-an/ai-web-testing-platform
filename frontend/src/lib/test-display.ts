import type { TestApiResponse } from "@/services/test-api";

export function extractHostname(rawUrl?: string | null): string {
  const value = String(rawUrl ?? "").trim();
  if (!value) {
    return "unknown";
  }

  const normalized = value.startsWith("http") ? value : `https://${value}`;
  try {
    const host = new URL(normalized).hostname.toLowerCase();
    return host.startsWith("www.") ? host.slice(4) : host;
  } catch {
    return value;
  }
}

export function resolveTestDisplayName(test: Partial<TestApiResponse> | undefined): string {
  if (!test) {
    return "Unnamed Test";
  }

  const candidates = [
    test.test_name,
    test.project,
    test.goal,
    test.ai_plan?.instruction,
    test.ai_summary,
    extractHostname(test.target_url || test.url),
    test.test_id,
  ];

  for (const candidate of candidates) {
    const text = String(candidate ?? "").trim();
    if (text.length > 0) {
      return text;
    }
  }

  return "Unnamed Test";
}

export function truncateText(text: string, limit: number): string {
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, Math.max(0, limit - 3)).trimEnd()}...`;
}
