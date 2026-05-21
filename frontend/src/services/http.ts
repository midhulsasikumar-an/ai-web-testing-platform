const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const AUTH_STORAGE_KEY = "signaltrack.auth.session";

export type AuthSession = {
  token: string;
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
};

export function getStoredAuthSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export function storeAuthSession(session: AuthSession): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getAuthToken(): string | null {
  return getStoredAuthSession()?.token ?? null;
}

export function buildAuthHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders);
  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const headers = buildAuthHeaders(init.headers);
  console.debug("[apiFetch] request", { url, method: init.method || "GET" });
  const response = await fetch(url, {
    ...init,
    headers,
  });

  console.debug("[apiFetch] response", { url, status: response.status, statusText: response.statusText });

  if (!response.ok) {
    const body = await response.text();
    console.error("API Error:", response.status, response.statusText, { url, body });
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response;
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init);
  return response.json() as Promise<T>;
}

export { API_BASE_URL };
