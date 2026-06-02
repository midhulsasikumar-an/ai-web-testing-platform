import { Terminal } from "lucide-react";

export default function GlobalLoading() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center text-slate-500">
      <Terminal className="h-8 w-8 animate-pulse text-blue-500" aria-hidden="true" />
      <p className="text-sm">Loading…</p>
    </div>
  );
}
