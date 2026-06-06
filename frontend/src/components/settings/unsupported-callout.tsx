"use client";

import { ReactNode } from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface UnsupportedCalloutProps {
  title: string;
  description: ReactNode;
  className?: string;
}

export function UnsupportedCallout({ title, description, className }: UnsupportedCalloutProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-2.5 rounded-lg border border-slate-200 bg-slate-50/80 px-3.5 py-3 text-[12.5px] text-slate-600",
        className
      )}
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
      <div>
        <p className="font-semibold text-slate-700">{title}</p>
        <p className="mt-0.5 text-slate-500">{description}</p>
      </div>
    </div>
  );
}
