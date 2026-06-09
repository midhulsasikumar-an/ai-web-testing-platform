import Link from "next/link";

export default function SupportPage() {
  return (
    <main className="min-h-screen bg-white px-6 py-10 text-slate-900">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <Link href="/login" className="text-sm font-medium text-blue-700 hover:text-blue-800">
          Back to sign in
        </Link>
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-blue-700">TestPulse AI</p>
          <h1 className="text-3xl font-semibold tracking-tight">Support</h1>
          <p className="text-sm leading-6 text-slate-600">
            For local development issues, start by checking backend health, MongoDB connectivity, browser
            dependencies, and authentication status.
          </p>
        </div>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Useful checks</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600">
            <li>Backend health: <code className="rounded bg-slate-100 px-1">/health</code></li>
            <li>Frontend API URL: <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_API_URL</code></li>
            <li>Backend tests: <code className="rounded bg-slate-100 px-1">npm run test:backend</code></li>
          </ul>
        </section>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Account help</h2>
          <p className="text-sm leading-6 text-slate-600">
            If you cannot sign in, confirm the backend is running and the JWT secret, MongoDB URL, and CORS origins
            are configured for the current environment.
          </p>
        </section>
      </div>
    </main>
  );
}
