import Link from "next/link";
import { Compass } from "lucide-react";

export default function GlobalNotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="rounded-full bg-slate-100 p-3 text-slate-600">
        <Compass className="h-8 w-8" aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Page not found</h2>
        <p className="mt-2 max-w-md text-sm text-slate-600">
          The page you tried to open does not exist or has been moved.
        </p>
      </div>
      <Link
        href="/dashboard"
        className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
