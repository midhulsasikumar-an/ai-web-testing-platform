"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Mail, Shield, User, UserCog, Calendar, Hash, Lock, CheckCircle2, Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Header } from "@/components/layout/header";
import { SettingsSection } from "@/components/settings/settings-section";
import { SettingsFormField } from "@/components/settings/settings-form-field";
import { SettingsStatus } from "@/components/settings/settings-status";
import { EmptyState } from "@/components/shared/empty-state";
import { AvatarCircle } from "@/components/shared/avatar-circle";
import { fetchAccountDetails, toAccountErrorMessage, updateAccountDetails, type AccountDetails } from "@/services/profile-api";
import { useAuth } from "@/context/auth-context";
import { getStoredAuthToken } from "@/services/http";
import { formatDateTime } from "@/lib/session";

type LoadState = "loading" | "ready" | "error";
type SaveState = "idle" | "loading" | "success" | "error";

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { user, token: contextToken, refreshUser } = useAuth();
  const [details, setDetails] = useState<AccountDetails | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const token = contextToken ?? getStoredAuthToken();
        const account = await fetchAccountDetails(token);
        if (!active) return;
        setDetails(account);
        setName(account.name);
        setEmail(account.email);
        setState("ready");
      } catch (error) {
        if (!active) return;
        setErrorMessage(toAccountErrorMessage(error));
        setState("error");
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [contextToken]);

  const display = useMemo<AccountDetails>(
    () => details ?? {
      id: user?.id ?? "—",
      name: user?.name ?? "—",
      email: user?.email ?? "—",
      role: user?.role ?? "user",
    },
    [details, user]
  );

  const navigateToSecurity = () => {
    router.push("/settings/security");
  };

  const hasChanges = name.trim() !== display.name || email.trim().toLowerCase() !== display.email.toLowerCase();
  const canSave = hasChanges && name.trim().length >= 2 && email.includes("@") && saveState !== "loading";

  const resetForm = () => {
    setName(display.name);
    setEmail(display.email);
    setSaveState("idle");
    setSaveError(null);
  };

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSave) return;
    setSaveState("loading");
    setSaveError(null);
    try {
      const updated = await updateAccountDetails(
        { name: name.trim(), email: email.trim() },
        contextToken ?? getStoredAuthToken()
      );
      setDetails(updated);
      setName(updated.name);
      setEmail(updated.email);
      await refreshUser();
      setSaveState("success");
      window.setTimeout(() => setSaveState("idle"), 3000);
    } catch (error) {
      setSaveError(toAccountErrorMessage(error));
      setSaveState("error");
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Profile"
        description="Personal information and account details for the signed-in user."
        eyebrow="Settings"
      />

      {state === "error" ? (
        <div className="rounded-xl border border-red-200 bg-red-50/60 p-4">
          <EmptyState
            icon={UserCog}
            title="Couldn’t load account details"
            description={errorMessage ?? "Please retry in a moment."}
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setState("loading");
                  setErrorMessage(null);
                  void (async () => {
                    try {
                      const account = await fetchAccountDetails(contextToken ?? getStoredAuthToken());
                      setDetails(account);
                      setName(account.name);
                      setEmail(account.email);
                      setState("ready");
                    } catch (error) {
                      setErrorMessage(toAccountErrorMessage(error));
                      setState("error");
                    }
                  })();
                }}
              >
                Retry
              </Button>
            }
          />
        </div>
      ) : null}

      <SettingsSection
        title="Account"
        description="Identity information from the active session."
        icon={<User className="h-4 w-4" />}
        action={state === "loading" ? <SettingsStatus status="loading" loadingLabel="Loading account…" /> : null}
      >
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <AvatarCircle name={display.name} size="lg" className="!h-16 !w-16 !text-base" />
          <div className="space-y-1">
            <p className="text-[14px] font-semibold text-slate-900">{display.name || "Unnamed user"}</p>
            <p className="text-[12.5px] text-slate-500">{display.email || "—"}</p>
            <p className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-slate-600">
              <Shield className="h-3 w-3" />
              {display.role}
            </p>
          </div>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Account information"
        description="Details provided by the authentication service."
        icon={<Hash className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">User ID</p>
            <p className="truncate rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 font-mono text-[12px] text-slate-700">
              {display.id}
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">Role</p>
            <p className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-[12.5px] capitalize text-slate-700">
              {display.role}
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">Email</p>
            <p className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-[12.5px] text-slate-700">
              <Mail className="h-3.5 w-3.5 text-slate-400" />
              {display.email}
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">Display name</p>
            <p className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-[12.5px] text-slate-700">
              {display.name}
            </p>
          </div>
        </div>
        <p className="text-[11.5px] text-slate-500">Profile changes update the signed-in account immediately.</p>
      </SettingsSection>

      <SettingsSection
        title="Display preferences"
        description="Account-level display values that travel with your session."
        icon={<UserCog className="h-4 w-4" />}
        footer={
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SettingsStatus
              status={saveState}
              errorMessage={saveError}
              successLabel="Profile updated"
              loadingLabel="Saving profile…"
            />
            <div className="flex items-center gap-2 sm:ml-auto">
              <Button type="button" variant="outline" size="sm" onClick={resetForm} disabled={!hasChanges || saveState === "loading"}>
                Reset
              </Button>
              <Button type="submit" size="sm" form="profile-form" disabled={!canSave}>
                {saveState === "loading" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save profile
              </Button>
            </div>
          </div>
        }
      >
        <form id="profile-form" className="space-y-4" onSubmit={saveProfile}>
          <SettingsFormField label="Display name" htmlFor="display-name" required>
            <Input
              id="display-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              minLength={2}
              disabled={saveState === "loading" || state === "loading"}
            />
          </SettingsFormField>
          <SettingsFormField
            label="Email"
            htmlFor="email"
            required
            description="Used for sign-in and account notifications."
          >
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              disabled={saveState === "loading" || state === "loading"}
            />
          </SettingsFormField>
        </form>
      </SettingsSection>

      <SettingsSection
        title="Security"
        description="Quick links to password and session controls."
        icon={<KeyRound className="h-4 w-4" />}
        action={
          <Button variant="outline" size="sm" onClick={navigateToSecurity}>
            <Lock className="h-3.5 w-3.5" />
            Open security
          </Button>
        }
      >
        <p className="text-[12.5px] text-slate-600">
          Manage your password, view the active session, and sign out from this device on the Security page.
        </p>
        <ul className="space-y-1.5 text-[12.5px] text-slate-600">
          <li className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            Sign in is currently active
          </li>
          <li className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            Session refreshed {formatDateTime(new Date())}
          </li>
        </ul>
      </SettingsSection>
    </div>
  );
}
