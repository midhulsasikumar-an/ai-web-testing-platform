"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (typeof window !== "undefined" && error) {
      // eslint-disable-next-line no-console
      console.error("Route error boundary caught:", error);
    }
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="rounded-full bg-amber-100 p-3 text-amber-700">
        <AlertTriangle className="h-8 w-8" aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Something went wrong.</h2>
        <p className="mt-2 max-w-md text-sm text-slate-600">
          {error?.message
            ? error.message
            : "An unexpected error occurred while loading this view. Please try again."}
        </p>
        {error?.digest ? (
          <p className="mt-1 text-xs text-slate-400">Error ID: {error.digest}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          <RefreshCcw className="h-4 w-4" />
          Try again
        </button>
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
