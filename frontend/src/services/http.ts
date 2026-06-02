import { API_BASE_URL, buildApiUrl } from "@/config/api";

const AUTH_STORAGE_KEY = "auth_token";
const REFRESH_STORAGE_KEY = "auth_refresh_token";
const AUTH_TOKEN_CLEARED_EVENT = "auth-token-cleared";

export class ApiHttpError extends Error {
  status: number;
  url: string;
  body: string;

  constructor(status: number, url: string, body: string, message?: string) {
    super(message || `Request failed with status ${status}`);
    this.name = "ApiHttpError";
    this.status = status;
    this.url = url;
    this.body = body;
  }
}

export type ApiFetchOptions = {
  auth?: boolean;
  authToken?: string | null;
  skipAuthRefresh?: boolean;
};

export function getStoredAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage.getItem(AUTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeAuthToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeRefreshToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(REFRESH_STORAGE_KEY, token);
}

export function clearRefreshToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(REFRESH_STORAGE_KEY);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent(AUTH_TOKEN_CLEARED_EVENT));
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(buildApiUrl("/api/auth/refresh"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      token?: string;
      access_token?: string;
      refresh_token?: string;
    };
    const nextToken = (data.access_token || data.token || "").trim();
    if (!nextToken) {
      return null;
    }

    storeAuthToken(nextToken);
    if (data.refresh_token && data.refresh_token.trim()) {
      storeRefreshToken(data.refresh_token.trim());
    }
    return nextToken;
  } catch {
    return null;
  }
}

export function buildAuthHeaders(initHeaders?: HeadersInit, token?: string | null): Headers {
  const headers = new Headers(initHeaders);
  const resolvedToken = token ?? getStoredAuthToken();
  if (resolvedToken) {
    headers.set("Authorization", `Bearer ${resolvedToken}`);
  }
  return headers;
}

export async function apiFetch(path: string, init: RequestInit = {}, options: ApiFetchOptions = {}): Promise<Response> {
  const url = buildApiUrl(path);
  const resolvedToken = options.auth === false ? options.authToken ?? null : options.authToken;
  const headers = buildAuthHeaders(init.headers, resolvedToken);

  let response = await fetch(url, {
    ...init,
    headers,
  });

  if (response.status === 401 && options.skipAuthRefresh !== true) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      const retryHeaders = buildAuthHeaders(init.headers, options.auth === false ? options.authToken ?? null : refreshedToken);
      response = await fetch(url, {
        ...init,
        headers: retryHeaders,
      });
    }
  }

  if (!response.ok) {
    const body = await response.text();
    if (response.status === 401) {
      clearRefreshToken();
      clearAuthToken();
    }
    throw new ApiHttpError(response.status, url, body, `Request failed: ${response.status} ${response.statusText}`);
  }

  return response;
}

export async function apiJson<T>(path: string, init: RequestInit = {}, options: ApiFetchOptions = {}): Promise<T> {
  const response = await apiFetch(path, init, options);
  return response.json() as Promise<T>;
}

export function onAuthTokenCleared(handler: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const listener = () => handler();
  window.addEventListener(AUTH_TOKEN_CLEARED_EVENT, listener);
  return () => window.removeEventListener(AUTH_TOKEN_CLEARED_EVENT, listener);
}

export { API_BASE_URL };
