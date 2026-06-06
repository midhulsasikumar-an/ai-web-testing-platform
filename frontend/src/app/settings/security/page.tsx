"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  KeyRound,
  Laptop,
  Loader2,
  Lock,
  LogOut,
  Monitor,
  Shield,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Header } from "@/components/layout/header";
import { SettingsSection } from "@/components/settings/settings-section";
import { SettingsFormField } from "@/components/settings/settings-form-field";
import { SettingsStatus, StatusPill } from "@/components/settings/settings-status";
import { UnsupportedCallout } from "@/components/settings/unsupported-callout";
import { changePassword, revokeAllSessions, toAccountErrorMessage } from "@/services/profile-api";
import { useAuth } from "@/context/auth-context";
import { getStoredAuthToken } from "@/services/http";
import { decodeSession, detectBrowser, formatDateTime, formatRelativeTime } from "@/lib/session";
import { cn } from "@/lib/utils";

type ActionStatus = "idle" | "loading" | "success" | "error";

const MIN_PASSWORD = 6;

function passwordIssues(value: string): string[] {
  const issues: string[] = [];
  if (value.length < MIN_PASSWORD) issues.push(`At least ${MIN_PASSWORD} characters`);
  if (!/[A-Za-z]/.test(value)) issues.push("At least one letter");
  if (!/[0-9]/.test(value)) issues.push("At least one number");
  return issues;
}

export default function SecuritySettingsPage() {
  const router = useRouter();
  const { user, token, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<ActionStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const [revokeStatus, setRevokeStatus] = useState<ActionStatus>("idle");
  const [revokeError, setRevokeError] = useState<string | null>(null);
  const [revokeMessage, setRevokeMessage] = useState<string | null>(null);

  const session = useMemo(() => decodeSession(token ?? getStoredAuthToken()), [token]);
  const browser = useMemo(
    () => (typeof navigator === "undefined" ? { name: "Unknown browser", os: "Unknown OS" } : detectBrowser(navigator.userAgent)),
    []
  );

  useEffect(() => {
    if (status !== "success") return;
    const timer = window.setTimeout(() => setStatus("idle"), 4000);
    return () => window.clearTimeout(timer);
  }, [status]);

  useEffect(() => {
    if (revokeStatus !== "success") return;
    const timer = window.setTimeout(() => setRevokeStatus("idle"), 4000);
    return () => window.clearTimeout(timer);
  }, [revokeStatus]);

  const passwordChecks = useMemo(() => passwordIssues(next), [next]);
  const passwordStrong = passwordChecks.length === 0 && next.length > 0;
  const confirmMatches = confirm === next && confirm.length > 0;

  const canSubmit =
    current.length > 0 &&
    passwordStrong &&
    confirmMatches &&
    status !== "loading";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;

    setStatus("loading");
    setError(null);
    try {
      const result = await changePassword(
        { currentPassword: current, newPassword: next },
        token ?? getStoredAuthToken()
      );
      setStatus("success");
      setCurrent("");
      setNext("");
      setConfirm("");
      if (result.revokedSessions) {
        window.setTimeout(() => {
          logout();
          router.replace("/login");
        }, 1200);
      }
    } catch (err) {
      setStatus("error");
      setError(toAccountErrorMessage(err));
    }
  };

  const handleRevokeAll = async () => {
    setRevokeStatus("loading");
    setRevokeError(null);
    setRevokeMessage(null);
    try {
      await revokeAllSessions(token ?? getStoredAuthToken());
      setRevokeStatus("success");
      setRevokeMessage("All other sessions have been revoked.");
    } catch (err) {
      const message = toAccountErrorMessage(err);
      setRevokeStatus("error");
      setRevokeError(message);
    }
  };

  const handleSignOutCurrent = () => {
    logout();
    router.replace("/login");
  };

  const accountAgeLabel = session?.issuedAt ? formatDateTime(session.issuedAt) : "—";
  const expiryLabel = session?.expiresAt ? formatDateTime(session.expiresAt) : "—";
  const expiryRelative = session?.expiresAt ? formatRelativeTime(session.expiresAt) : "—";

  const isUnsupported = (msg: string | null) =>
    Boolean(msg && /not available|not exposed|not implemented|contact/i.test(msg));

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Security"
        description="Authentication, password, and active session controls."
        eyebrow="Settings"
      />

      <SettingsSection
        title="Change password"
        description="Update the password associated with your account."
        icon={<KeyRound className="h-4 w-4" />}
        footer={
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SettingsStatus
              status={status}
              errorMessage={error}
              successLabel={status === "success" ? "Password updated. Re-authenticating…" : undefined}
              loadingLabel="Updating password…"
            />
            <div className="flex items-center gap-2 sm:ml-auto">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setCurrent("");
                  setNext("");
                  setConfirm("");
                  setStatus("idle");
                  setError(null);
                }}
                disabled={status === "loading"}
              >
                Clear
              </Button>
              <Button
                type="submit"
                size="sm"
                form="change-password-form"
                disabled={!canSubmit}
              >
                {status === "loading" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Lock className="h-3.5 w-3.5" />}
                Update password
              </Button>
            </div>
          </div>
        }
      >
        <form id="change-password-form" onSubmit={handleSubmit} className="space-y-4">
          <SettingsFormField label="Current password" htmlFor="current-password" required>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              placeholder="••••••••"
              required
              disabled={status === "loading"}
            />
          </SettingsFormField>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingsFormField
              label="New password"
              htmlFor="new-password"
              required
              description="At least 6 characters, including a letter and a number."
            >
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(event) => setNext(event.target.value)}
                placeholder="••••••••"
                required
                disabled={status === "loading"}
              />
              {next.length > 0 ? (
                <ul className="mt-1.5 space-y-1 text-[11.5px]">
                  {passwordChecks.length === 0 ? (
                    <li className="flex items-center gap-1.5 text-emerald-700">
                      <ShieldCheck className="h-3 w-3" /> Strong enough
                    </li>
                  ) : (
                    passwordChecks.map((issue) => (
                      <li key={issue} className="flex items-center gap-1.5 text-slate-500">
                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300" /> {issue}
                      </li>
                    ))
                  )}
                </ul>
              ) : null}
            </SettingsFormField>
            <SettingsFormField
              label="Confirm new password"
              htmlFor="confirm-password"
              required
              description={confirm.length > 0 && !confirmMatches ? "Passwords do not match." : undefined}
              error={confirm.length > 0 && !confirmMatches ? "Passwords do not match." : null}
            >
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                placeholder="••••••••"
                required
                disabled={status === "loading"}
                aria-invalid={confirm.length > 0 && !confirmMatches}
                className={cn(
                  confirm.length > 0 && !confirmMatches && "border-red-300 focus-visible:ring-red-500/20"
                )}
              />
            </SettingsFormField>
          </div>
          {status === "error" && isUnsupported(error) ? (
            <UnsupportedCallout
              title="Password changes aren't available yet"
              description="The current backend does not expose a password change endpoint. Until it does, please sign out and use the signup flow to set a new password or contact your administrator."
            />
          ) : null}
        </form>
      </SettingsSection>

      <SettingsSection
        title="Active session"
        description="The session attached to this browser. Log out when you finish."
        icon={<Monitor className="h-4 w-4" />}
        footer={
          <div className="flex w-full items-center justify-between gap-3">
            <p className="text-[12px] text-slate-500">
              Sign out revokes this access token via /api/auth/logout.
            </p>
            <Button variant="outline" size="sm" onClick={handleSignOutCurrent}>
              <LogOut className="h-3.5 w-3.5" />
              Sign out of this device
            </Button>
          </div>
        }
      >
        <div className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <SessionDetail label="Account" value={user?.email ?? "—"} icon={Shield} />
          <SessionDetail label="Browser / OS" value={`${browser.name} · ${browser.os}`} icon={Laptop} />
          <SessionDetail label="Signed in" value={accountAgeLabel} icon={Smartphone} />
          <SessionDetail label="Token expires" value={`${expiryLabel} (${expiryRelative})`} icon={Lock} />
        </div>
      </SettingsSection>

      <SettingsSection
        title="Account security status"
        description="High-level signals from the active session."
        icon={<ShieldCheck className="h-4 w-4" />}
      >
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <SecurityRow
            label="Authentication"
            value="Password"
            status="ok"
            note="Issued access token is valid"
          />
          <SecurityRow
            label="Two-factor authentication"
            value="Not enabled"
            status="warning"
            note="No 2FA endpoint is exposed by the current backend"
          />
          <SecurityRow
            label="Session token"
            value={session ? "Active" : "Unknown"}
            status={session ? "ok" : "muted"}
            note={session ? "Decoded from the active JWT" : "Unable to decode session token"}
          />
          <SecurityRow
            label="Other devices"
            value="Not tracked"
            status="muted"
            note="The backend does not expose a session listing endpoint"
          />
        </ul>
      </SettingsSection>

      <SettingsSection
        title="Revoke other sessions"
        description="Invalidate access tokens held by other devices signed in to this account."
        icon={<LogOut className="h-4 w-4" />}
        footer={
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SettingsStatus
              status={revokeStatus}
              errorMessage={revokeError}
              successLabel={revokeMessage ?? "Other sessions revoked"}
              loadingLabel="Revoking other sessions…"
            />
            <Button
              variant="destructive"
              size="sm"
              onClick={handleRevokeAll}
              disabled={revokeStatus === "loading"}
            >
              {revokeStatus === "loading" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogOut className="h-3.5 w-3.5" />}
              Revoke all other sessions
            </Button>
          </div>
        }
      >
        <UnsupportedCallout
          title="This action depends on a backend endpoint"
          description="If the backend exposes /api/auth/sessions/revoke-all it will be invoked here. Otherwise the request fails safely and you'll see an explanatory error below — no other devices are affected."
        />
        {revokeStatus === "error" ? (
          <p className="text-[12px] text-red-600">
            {isUnsupported(revokeError)
              ? "Revoking all sessions isn't supported by the current backend. Only this device can be signed out for now."
              : revokeError}
          </p>
        ) : null}
      </SettingsSection>
    </div>
  );
}

function SessionDetail({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="flex items-center gap-1.5 text-[12.5px] text-slate-700">
        <Icon className="h-3.5 w-3.5 text-slate-400" />
        <span className="truncate">{value}</span>
      </p>
    </div>
  );
}

function SecurityRow({
  label,
  value,
  status,
  note,
}: {
  label: string;
  value: string;
  status: "ok" | "warning" | "error" | "muted";
  note: string;
}) {
  return (
    <li className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5">
      <div className="min-w-0">
        <p className="text-[12.5px] font-semibold text-slate-800">{label}</p>
        <p className="truncate text-[11.5px] text-slate-500">{note}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-[12px] font-medium text-slate-700">{value}</span>
        <StatusPill status={status} />
      </div>
    </li>
  );
}
