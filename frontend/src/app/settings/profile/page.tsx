"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Mail, Shield, User, UserCog, Calendar, Hash, Lock, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Header } from "@/components/layout/header";
import { SettingsSection } from "@/components/settings/settings-section";
import { SettingsFormField } from "@/components/settings/settings-form-field";
import { SettingsStatus } from "@/components/settings/settings-status";
import { UnsupportedCallout } from "@/components/settings/unsupported-callout";
import { EmptyState } from "@/components/shared/empty-state";
import { AvatarCircle } from "@/components/shared/avatar-circle";
import { fetchAccountDetails, toAccountErrorMessage, type AccountDetails } from "@/services/profile-api";
import { useAuth } from "@/context/auth-context";
import { getStoredAuthToken } from "@/services/http";
import { formatDateTime } from "@/lib/session";

type LoadState = "loading" | "ready" | "error";

function initialsFromName(name: string | undefined | null): string {
  if (!name) return "U";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { user, token: contextToken } = useAuth();
  const [details, setDetails] = useState<AccountDetails | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const token = contextToken ?? getStoredAuthToken();
        const account = await fetchAccountDetails(token);
        if (!active) return;
        setDetails(account);
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
        description="Read-only details provided by the authentication service."
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
        <p className="text-[11.5px] text-slate-500">
          Account fields are managed by the authentication service. Updates are not exposed through the API.
        </p>
      </SettingsSection>

      <SettingsSection
        title="Display preferences"
        description="Account-level display values that travel with your session."
        icon={<UserCog className="h-4 w-4" />}
      >
        <SettingsFormField label="Display name" htmlFor="display-name">
          <Input
            id="display-name"
            value={display.name}
            readOnly
            className="cursor-default bg-slate-50/60"
          />
        </SettingsFormField>
        <SettingsFormField
          label="Email"
          htmlFor="email"
          description="Used for sign-in and account notifications."
        >
          <Input
            id="email"
            type="email"
            value={display.email}
            readOnly
            className="cursor-default bg-slate-50/60"
          />
        </SettingsFormField>
        <UnsupportedCallout
          title="Editing profile fields is not available"
          description="The current backend exposes a read-only /api/auth/me endpoint. To change your name or email, contact the workspace administrator."
        />
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
