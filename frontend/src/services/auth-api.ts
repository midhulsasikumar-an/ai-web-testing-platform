import { API_BASE_URL, API_HEALTH_PATH, AUTH_TIMEOUT_MS, buildApiUrl } from "@/config/api";
import { type AuthSession } from "@/services/http";

export type SignupResponse = {
  token: string;
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

type ApiErrorBody = {
  detail?: string;
  message?: string;
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

async function parseResponseBodySafe(response: Response): Promise<ApiErrorBody | unknown> {
  const raw = await response.text();
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return { message: raw };
  }
}

function withTimeoutSignal(timeoutMs: number): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cleanup: () => window.clearTimeout(timeoutId),
  };
}

export async function checkBackendHealth(force = false): Promise<void> {
  const now = Date.now();
  if (!force && now - lastHealthCheckMs < HEALTH_CHECK_TTL_MS) {
    return;
  }

  const healthUrl = buildApiUrl(API_HEALTH_PATH);
  const { signal, cleanup } = withTimeoutSignal(Math.min(AUTH_TIMEOUT_MS, 5000));

  console.info("[auth-api] health request", { url: healthUrl });

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
    console.info("[auth-api] health response", { url: healthUrl, status: response.status });
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

  console.info("[auth-api] request", { method, url, apiBaseUrl: API_BASE_URL });

  try {
    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: method === "GET" ? undefined : JSON.stringify(body),
      signal,
    });

    console.info("[auth-api] response", { method, url, status: response.status, ok: response.ok });

    if (!response.ok) {
      const errorBody = (await parseResponseBodySafe(response)) as ApiErrorBody;
      const detail = errorBody.detail || errorBody.message || "Authentication request failed.";

      if (response.status === 401) {
        throw new AuthApiError("INVALID_CREDENTIALS", "Invalid credentials.", {
          status: response.status,
          url,
        });
      }

      if (response.status === 409) {
        throw new AuthApiError("CONFLICT", detail, {
          status: response.status,
          url,
        });
      }

      if (response.status >= 500) {
        throw new AuthApiError("SERVER_ERROR", "Authentication service unavailable.", {
          status: response.status,
          url,
        });
      }

      throw new AuthApiError("SERVER_ERROR", detail, {
        status: response.status,
        url,
      });
    }

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
    if (error instanceof AuthApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AuthApiError("TIMEOUT", "Authentication service unavailable (request timed out).", {
        url,
        cause: error,
      });
    }

    if (error instanceof TypeError) {
      throw new AuthApiError(
        "NETWORK_ERROR",
        "Network error: Unable to reach authentication service. Check API URL, CORS, and backend status.",
        { url, cause: error }
      );
    }

    throw new AuthApiError("SERVER_ERROR", "Authentication request failed.", {
      url,
      cause: error,
    });
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
  return {
    token: data.token,
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
  return {
    token: data.token,
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    },
  };
}

export async function getCurrentUser(token: string): Promise<MeResponse["user"]> {
  const url = buildApiUrl("/api/auth/me");
  const { signal, cleanup } = withTimeoutSignal(AUTH_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AuthApiError("TIMEOUT", "Authentication service unavailable (request timed out).", {
        url,
      });
    }
    if (error instanceof TypeError) {
      throw new AuthApiError("NETWORK_ERROR", "Network error: Unable to validate session.", {
        url,
      });
    }
    throw error;
  } finally {
    cleanup();
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new AuthApiError("UNAUTHORIZED", "Unauthorized", {
        status: response.status,
        url,
      });
    }

    const body = await parseResponseBodySafe(response);
    console.error("[auth-api] API error", {
      url,
      status: response.status,
      body,
    });
    throw new AuthApiError("SERVER_ERROR", `Session validation failed: ${response.status}`, {
      status: response.status,
      url,
    });
  }

  const data = (await response.json()) as MeResponse;
  return data.user;
}
