import { ApiHttpError, apiFetch } from "@/services/http";

export type AccountDetails = {
  id: string;
  name: string;
  email: string;
  role: string;
};

export type ChangePasswordPayload = {
  currentPassword: string;
  newPassword: string;
};

export class AccountApiError extends Error {
  code: "BACKEND_UNAVAILABLE" | "NETWORK_ERROR" | "INVALID_CREDENTIALS" | "UNSUPPORTED" | "SERVER_ERROR";
  status?: number;

  constructor(
    code: AccountApiError["code"],
    message: string,
    options?: { status?: number; cause?: unknown }
  ) {
    super(message);
    this.name = "AccountApiError";
    this.code = code;
    this.status = options?.status;
    if (options?.cause) this.cause = options.cause;
  }
}

function normalizeError(error: unknown, fallbackMessage: string): AccountApiError {
  if (error instanceof AccountApiError) return error;
  if (error instanceof ApiHttpError) {
    if (error.status === 401 || error.status === 403) {
      return new AccountApiError("INVALID_CREDENTIALS", error.body || "The current password is incorrect.", { status: error.status, cause: error });
    }
    if (error.status === 404 || error.status === 405 || error.status === 501) {
      return new AccountApiError("UNSUPPORTED", "This action is not available on the current backend.", { status: error.status, cause: error });
    }
    if (error.status >= 500) {
      return new AccountApiError("SERVER_ERROR", "Account service is temporarily unavailable.", { status: error.status, cause: error });
    }
    return new AccountApiError("SERVER_ERROR", error.body || fallbackMessage, { status: error.status, cause: error });
  }
  if (error instanceof TypeError) {
    return new AccountApiError("BACKEND_UNAVAILABLE", "Backend is not reachable. Please try again shortly.", { cause: error });
  }
  return new AccountApiError("SERVER_ERROR", fallbackMessage, { cause: error });
}

export async function fetchAccountDetails(token?: string | null): Promise<AccountDetails> {
  try {
    const response = await apiFetch(
      "/api/auth/me",
      { method: "GET" },
      { authToken: token ?? null }
    );
    const data = (await response.json()) as { user: AccountDetails };
    return data.user;
  } catch (error) {
    throw normalizeError(error, "Unable to load account information.");
  }
}

export async function changePassword(
  payload: ChangePasswordPayload,
  token?: string | null
): Promise<{ revokedSessions: boolean }> {
  try {
    const response = await apiFetch(
      "/api/auth/password",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: payload.currentPassword,
          new_password: payload.newPassword,
        }),
      },
      { authToken: token ?? null }
    );
    const data = (await response.json().catch(() => ({}))) as { revoked_sessions?: boolean };
    return { revokedSessions: Boolean(data.revoked_sessions) };
  } catch (error) {
    throw normalizeError(error, "Unable to change password.");
  }
}

export async function revokeAllSessions(token?: string | null): Promise<{ revoked: number }> {
  try {
    const response = await apiFetch(
      "/api/auth/sessions/revoke-all",
      { method: "POST" },
      { authToken: token ?? null }
    );
    const data = (await response.json().catch(() => ({}))) as { revoked?: number };
    return { revoked: Number(data.revoked ?? 0) };
  } catch (error) {
    throw normalizeError(error, "Unable to revoke other sessions.");
  }
}

export function toAccountErrorMessage(error: unknown): string {
  if (error instanceof AccountApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return "Something went wrong. Please try again.";
}
