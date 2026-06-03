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

type TestLike = {
  test_name?: string | null;
  name?: string | null;
  title?: string | null;
  project?: string | null;
  goal?: string | null;
  ai_plan?: { instruction?: string | null; test_case?: { title?: string | null } | null } | null;
  ai_summary?: string | null;
  target_url?: string | null;
  url?: string | null;
  test_id?: string | null;
};

const FALLBACK_TEST_NAME = "Untitled Test";

export function resolveTestDisplayName(test: TestLike | undefined | null): string {
  if (!test) {
    return FALLBACK_TEST_NAME;
  }

  const candidates: Array<string | null | undefined> = [
    test.test_name,
    test.name,
    test.title,
    test.ai_plan?.test_case?.title,
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

  return FALLBACK_TEST_NAME;
}

export function truncateText(text: string, limit: number): string {
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, Math.max(0, limit - 3)).trimEnd()}...`;
}
