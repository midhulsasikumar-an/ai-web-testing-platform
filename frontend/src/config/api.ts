type ApiConfig = {
  apiBaseUrl: string;
  healthPath: string;
  authTimeoutMs: number;
};

const DEFAULT_HEALTH_PATH = "/health";
const DEFAULT_AUTH_TIMEOUT_MS = 10000;

function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function parseTimeout(rawValue: string | undefined): number {
  if (!rawValue) {
    return DEFAULT_AUTH_TIMEOUT_MS;
  }

  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_AUTH_TIMEOUT_MS;
  }

  return parsed;
}

function resolveApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "";
  const normalized = normalizeBaseUrl(raw);

  if (!normalized) {
    throw new Error("Missing NEXT_PUBLIC_API_URL environment variable");
  }

  try {
    const url = new URL(normalized);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("API URL must use http or https protocol");
    }
    return normalizeBaseUrl(url.toString());
  } catch (error) {
    throw new Error(
      `[api-config] Invalid NEXT_PUBLIC_API_URL value: ${normalized}. ${(error as Error).message}`
    );
  }
}

const apiConfig: ApiConfig = {
  apiBaseUrl: resolveApiBaseUrl(),
  healthPath: process.env.NEXT_PUBLIC_API_HEALTH_PATH || DEFAULT_HEALTH_PATH,
  authTimeoutMs: parseTimeout(process.env.NEXT_PUBLIC_AUTH_TIMEOUT_MS),
};

export const API_BASE_URL = apiConfig.apiBaseUrl;
export const API_HEALTH_PATH = apiConfig.healthPath;
export const AUTH_TIMEOUT_MS = apiConfig.authTimeoutMs;

export function buildApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function getApiConfig(): ApiConfig {
  return apiConfig;
}
