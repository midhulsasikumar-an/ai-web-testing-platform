import { API_HEALTH_PATH, AUTH_TIMEOUT_MS, buildApiUrl } from "@/config/api";
import { ApiHttpError, apiFetch } from "@/services/http";

export type SignupResponse = {
  token: string;
  access_token?: string;
  refresh_token?: string;
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
};

type MeResponse = {
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
};

export type AuthSession = {
  token: string;
  refreshToken: string | null;
  user: MeResponse["user"];
};

export class AuthApiError extends Error {
  code:
    | "BACKEND_UNAVAILABLE"
    | "NETWORK_ERROR"
    | "TIMEOUT"
    | "INVALID_RESPONSE"
    | "INVALID_CREDENTIALS"
    | "UNAUTHORIZED"
    | "CONFLICT"
    | "SERVER_ERROR";
  status?: number;
  url?: string;

  constructor(
    code: AuthApiError["code"],
    message: string,
    options?: { status?: number; url?: string; cause?: unknown }
  ) {
    super(message);
    this.name = "AuthApiError";
    this.code = code;
    this.status = options?.status;
    this.url = options?.url;
    if (options?.cause) {
      this.cause = options.cause;
    }
  }
}

let lastHealthCheckMs = 0;
const HEALTH_CHECK_TTL_MS = 15000;

function withTimeoutSignal(timeoutMs: number): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cleanup: () => window.clearTimeout(timeoutId),
  };
}

function isBackendUnavailableError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof DOMException && error.name === "AbortError");
}

function normalizeAuthApiError(error: unknown, fallbackMessage: string, url?: string): AuthApiError {
  if (error instanceof AuthApiError) {
    return error;
  }

  if (error instanceof ApiHttpError) {
    if (error.status === 401) {
      return new AuthApiError("UNAUTHORIZED", "Unauthorized", { status: error.status, url: error.url, cause: error });
    }

    if (error.status === 409) {
      return new AuthApiError("CONFLICT", error.body || fallbackMessage, { status: error.status, url: error.url, cause: error });
    }

    if (error.status >= 500) {
      return new AuthApiError("SERVER_ERROR", "Authentication service unavailable.", { status: error.status, url: error.url, cause: error });
    }

    return new AuthApiError("SERVER_ERROR", error.body || fallbackMessage, { status: error.status, url: error.url, cause: error });
  }

  if (isBackendUnavailableError(error)) {
    return new AuthApiError("BACKEND_UNAVAILABLE", fallbackMessage, { url, cause: error });
  }

  return new AuthApiError("SERVER_ERROR", fallbackMessage, { url, cause: error });
}

export async function checkBackendHealth(force = false): Promise<void> {
  const now = Date.now();
  if (!force && now - lastHealthCheckMs < HEALTH_CHECK_TTL_MS) {
    return;
  }

  const healthUrl = buildApiUrl(API_HEALTH_PATH);
  const { signal, cleanup } = withTimeoutSignal(Math.min(AUTH_TIMEOUT_MS, 5000));

  try {
    const response = await fetch(healthUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal,
    });

    if (!response.ok) {
      throw new AuthApiError(
        "BACKEND_UNAVAILABLE",
        "Backend server is not running.",
        { status: response.status, url: healthUrl }
      );
    }

    lastHealthCheckMs = now;
  } catch (error) {
    if (error instanceof AuthApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AuthApiError("TIMEOUT", "Authentication service unavailable (request timed out).", {
        url: healthUrl,
        cause: error,
      });
    }

    throw new AuthApiError("BACKEND_UNAVAILABLE", "Backend server is not running.", {
      url: healthUrl,
      cause: error,
    });
  } finally {
    cleanup();
  }
}

async function authRequest<T>(path: string, body: Record<string, string>, method: "POST" | "GET" = "POST"): Promise<T> {
  const url = buildApiUrl(path);
  const { signal, cleanup } = withTimeoutSignal(AUTH_TIMEOUT_MS);

  try {
    const response = await apiFetch(
      path,
      {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: method === "GET" ? undefined : JSON.stringify(body),
        signal,
      },
      { auth: false }
    );

    try {
      return (await response.json()) as T;
    } catch (error) {
      throw new AuthApiError("INVALID_RESPONSE", "Invalid response from authentication service.", {
        status: response.status,
        url,
        cause: error,
      });
    }
  } catch (error) {
    throw normalizeAuthApiError(error, "Authentication request failed.", url);
  } finally {
    cleanup();
  }
}

export function toAuthErrorMessage(error: unknown): string {
  if (error instanceof AuthApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Authentication failed.";
}

export async function signupWithBackend(name: string, email: string, password: string): Promise<AuthSession> {
  await checkBackendHealth();
  const data = await authRequest<SignupResponse>("/api/auth/signup", { name, email, password });
  const accessToken = (data.access_token || data.token || "").trim();
  return {
    token: accessToken,
    refreshToken: (data.refresh_token || "").trim() || null,
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    },
  };
}

export async function loginWithBackend(email: string, password: string): Promise<AuthSession> {
  await checkBackendHealth();
  const data = await authRequest<SignupResponse>("/api/auth/login", { email, password });
  const accessToken = (data.access_token || data.token || "").trim();
  return {
    token: accessToken,
    refreshToken: (data.refresh_token || "").trim() || null,
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    },
  };
}

export async function getCurrentUser(token?: string): Promise<MeResponse["user"]> {
  const url = buildApiUrl("/api/auth/me");
  const { signal, cleanup } = withTimeoutSignal(AUTH_TIMEOUT_MS);
  let response: Response;
  try {
    response = await apiFetch(
      "/api/auth/me",
      {
        method: "GET",
        signal,
      },
      { auth: false, authToken: token ?? null }
    );
  } catch (error) {
    throw normalizeAuthApiError(error, "Unable to validate session.", url);
  } finally {
    cleanup();
  }

  const data = (await response.json()) as MeResponse;
  return data.user;
}

export async function logoutWithBackend(token?: string): Promise<void> {
  const url = buildApiUrl("/api/auth/logout");
  const { signal, cleanup } = withTimeoutSignal(AUTH_TIMEOUT_MS);

  try {
    await apiFetch(
      "/api/auth/logout",
      {
        method: "POST",
        signal,
      },
      { auth: false, authToken: token ?? null, skipAuthRefresh: true }
    );
  } catch (error) {
    throw normalizeAuthApiError(error, "Unable to complete logout.", url);
  } finally {
    cleanup();
  }
}
