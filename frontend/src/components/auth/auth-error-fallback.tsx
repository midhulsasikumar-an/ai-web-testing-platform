"use client";

import Link from "next/link";

type AuthErrorFallbackProps = {
  title: string;
  message: string;
  onRetry: () => void;
};

export function AuthErrorFallback({ title, message, onRetry }: AuthErrorFallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white p-6">
      <div className="w-full max-w-lg rounded-xl border border-red-200 bg-red-50 p-6">
        <h1 className="text-xl font-semibold text-red-700">{title}</h1>
        <p className="mt-2 text-sm text-red-600">{message}</p>

        <div className="mt-6 flex items-center gap-3">
          <button
            type="button"
            onClick={onRetry}
            className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Try again
          </button>
          <Link href="/" className="px-4 py-2 rounded-md border border-red-300 text-red-700 hover:bg-red-100 transition-colors">
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}
