"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";

export function MobileNav({ open: externalOpen, onOpenChange }: { open?: boolean; onOpenChange?: (open: boolean) => void } = {}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const pathname = usePathname();
  const controlled = externalOpen !== undefined;
  const open = controlled ? externalOpen : internalOpen;
  const setOpen = (next: boolean) => {
    if (controlled) {
      onOpenChange?.(next);
    } else {
      setInternalOpen(next);
    }
  };

  useEffect(() => {
    // Closing the drawer on path change is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (open) setOpen(false);
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <>
      {open ? (
        <div
          aria-hidden="true"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm lg:hidden"
        />
      ) : null}

      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 transform bg-white shadow-xl transition-transform duration-200 ease-out lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-slate-200 px-3">
          <Link
            href="/dashboard"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 via-blue-600 to-indigo-600 text-white shadow-sm">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="text-[14px] font-semibold tracking-tight text-slate-900">
              TestPilot <span className="text-blue-600">AI</span>
            </span>
          </Link>
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <Sidebar variant="mobile" onNavigate={() => setOpen(false)} />
      </div>
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open navigation"
      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition-colors hover:bg-slate-50 lg:hidden"
    >
      <span className="block h-0.5 w-4 bg-current shadow-[0_-5px_0_currentColor,0_5px_0_currentColor]" />
    </button>
  );
}
