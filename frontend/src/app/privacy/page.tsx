import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-white px-6 py-10 text-slate-900">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <Link href="/login" className="text-sm font-medium text-blue-700 hover:text-blue-800">
          Back to sign in
        </Link>
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-blue-700">TestPulse AI</p>
          <h1 className="text-3xl font-semibold tracking-tight">Privacy</h1>
          <p className="text-sm leading-6 text-slate-600">
            TestPulse AI stores account details, test run metadata, generated reports, bugs, chat messages,
            screenshots, and execution artifacts so authenticated users can review testing history.
          </p>
        </div>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Data used by the app</h2>
          <p className="text-sm leading-6 text-slate-600">
            The platform uses submitted URLs, testing instructions, browser execution results, and optional AI
            workspace messages to generate plans, reports, and recommendations. API keys and secrets should be
            configured only through backend environment variables.
          </p>
        </section>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Account control</h2>
          <p className="text-sm leading-6 text-slate-600">
            Signed-in users can update profile details, change passwords, sign out, and invalidate other active
            tokens from Settings.
          </p>
        </section>
      </div>
    </main>
  );
}
