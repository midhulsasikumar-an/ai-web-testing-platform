"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SettingsFormFieldProps {
  label: string;
  htmlFor?: string;
  description?: ReactNode;
  error?: string | null;
  required?: boolean;
  trailing?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function SettingsFormField({
  label,
  htmlFor,
  description,
  error,
  required,
  trailing,
  className,
  children,
}: SettingsFormFieldProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor={htmlFor}
          className="text-[12px] font-medium text-slate-700"
        >
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </label>
        {trailing}
      </div>
      {children}
      {error ? (
        <p className="text-[11.5px] font-medium text-red-600">{error}</p>
      ) : description ? (
        <p className="text-[11.5px] text-slate-500">{description}</p>
      ) : null}
    </div>
  );
}
