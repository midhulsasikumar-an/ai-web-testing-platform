"use client";

interface AIHealthWidgetProps {
  score: number | null;
}

export function AIHealthWidget({ score }: AIHealthWidgetProps) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = typeof score === "number" ? circumference - (score / 100) * circumference : circumference;

  return (
    <div className="shell-surface rounded-xl border border-border p-5 shadow-xs-token flex flex-col items-center justify-between gap-3 col-span-1">
      <div className="w-full flex items-center justify-between">
        <h3 className="text-eyebrow">AI Health Score</h3>
        <span className="text-muted-sm">Live</span>
      </div>

      <div className="relative flex items-center justify-center my-1">
        <svg className="transform -rotate-90 w-32 h-32">
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="10"
            fill="transparent"
            className="text-slate-100"
          />
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="10"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="text-primary transition-all duration-1000 ease-in-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-slate-900 tracking-tight">{typeof score === "number" ? score : "—"}</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">{typeof score === "number" ? "/ 100" : ""}</span>
        </div>
      </div>
    </div>
  );
}
