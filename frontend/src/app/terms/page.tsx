import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-white px-6 py-10 text-slate-900">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <Link href="/login" className="text-sm font-medium text-blue-700 hover:text-blue-800">
          Back to sign in
        </Link>
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-blue-700">TestPulse AI</p>
          <h1 className="text-3xl font-semibold tracking-tight">Terms</h1>
          <p className="text-sm leading-6 text-slate-600">
            Use TestPulse AI only on websites and applications you own, operate, or have explicit permission to
            test. Automated browser testing can create traffic, form submissions, and account activity.
          </p>
        </div>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Responsible testing</h2>
          <p className="text-sm leading-6 text-slate-600">
            Do not use the platform to bypass access controls, abuse third-party services, harvest data, or run
            tests against targets where automated testing is not allowed.
          </p>
        </section>
        <section className="space-y-2 rounded-lg border border-slate-200 p-5">
          <h2 className="text-base font-semibold">Generated output</h2>
          <p className="text-sm leading-6 text-slate-600">
            AI-generated plans, bug summaries, and reports are assistance tools. Review findings before relying on
            them for release, compliance, or security decisions.
          </p>
        </section>
      </div>
    </main>
  );
}
