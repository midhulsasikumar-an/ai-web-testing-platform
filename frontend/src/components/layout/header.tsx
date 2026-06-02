"use client";

import { cn } from "@/lib/utils";

interface HeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  children?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function Header({ title, description, eyebrow, actions, children, className }: HeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 pb-2 sm:flex-row sm:items-end sm:justify-between",
        className
      )}
    >
      <div className="min-w-0 space-y-0.5">
        {eyebrow ? <span className="text-eyebrow">{eyebrow}</span> : null}
        <h1 className="text-h1 text-slate-900">{title}</h1>
        {description ? (
          <p className="text-[13px] leading-relaxed text-slate-500">{description}</p>
        ) : null}
      </div>
      {(actions || children) ? (
        <div className="flex flex-wrap items-center gap-2">{actions || children}</div>
      ) : null}
    </div>
  );
}
