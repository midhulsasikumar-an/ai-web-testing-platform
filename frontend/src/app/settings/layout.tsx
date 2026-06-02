"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Shield, User, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";

type SettingsNavItem = {
  name: string;
  href: string;
  icon: LucideIcon;
  description: string;
};

const navItems: SettingsNavItem[] = [
  { name: "Profile", href: "/settings/profile", icon: User, description: "Personal information" },
  { name: "Security", href: "/settings/security", icon: Shield, description: "Password & sessions" },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, user } = useAuth();

  const handleSignOut = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex flex-col gap-5 lg:flex-row">
      <aside className="lg:w-64 lg:shrink-0">
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-xs-token">
          <nav className="flex flex-col gap-0.5">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-all",
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  )}
                >
                  {isActive ? (
                    <span className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-blue-600" />
                  ) : null}
                  <span className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
                    isActive ? "bg-white text-blue-600 shadow-xs-token" : "bg-transparent text-slate-500 group-hover:bg-white"
                  )}>
                    <Icon className="h-3.5 w-3.5" strokeWidth={2.25} />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col leading-tight">
                    <span className="truncate">{item.name}</span>
                    <span className="truncate text-[11px] font-normal text-slate-500">{item.description}</span>
                  </span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-3 border-t border-slate-100 pt-3">
            <div className="px-2.5 pb-2.5">
              <p className="truncate text-[12px] font-semibold text-slate-800">
                {user?.name || "Signed in user"}
              </p>
              <p className="truncate text-[11px] text-slate-500">
                {user?.email || "—"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[12.5px] font-medium text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-md text-slate-400">
                <LogOut className="h-3.5 w-3.5" />
              </span>
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        {children}
      </main>
    </div>
  );
}
