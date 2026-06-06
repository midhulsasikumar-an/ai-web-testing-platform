"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type DashboardSectionProps = {
  id?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  storageKey?: string;
  compact?: boolean;
};

export function DashboardSection({
  id,
  title,
  description,
  actions,
  children,
  className,
  headerClassName,
  contentClassName,
  defaultOpen = true,
  open,
  onOpenChange,
  storageKey,
  compact = false,
}: DashboardSectionProps) {
  const [internalOpen, setInternalOpen] = useState(() => {
    if (typeof window === "undefined" || !storageKey || typeof open === "boolean") {
      return defaultOpen;
    }

    const saved = window.localStorage.getItem(storageKey);
    if (saved === "open") return true;
    if (saved === "closed") return false;
    return defaultOpen;
  });
  const isControlled = typeof open === "boolean";
  const isOpen = isControlled ? open : internalOpen;

  useEffect(() => {
    if (typeof window === "undefined" || !storageKey || isControlled) {
      return;
    }

    window.localStorage.setItem(storageKey, isOpen ? "open" : "closed");
  }, [isControlled, isOpen, storageKey]);

  const handleToggle = () => {
    const nextOpen = !isOpen;
    if (!isControlled) {
      setInternalOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  };

  return (
    <section
      id={id}
      className={cn(
        "rounded-xl border border-border bg-card text-sm text-card-foreground shadow-xs-token",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-start justify-between gap-3 border-b border-border bg-white px-4 py-3",
          compact && "sticky top-0 z-10",
          headerClassName,
        )}
      >
        <div className="min-w-0">
          <h2 className="truncate text-h3 text-slate-900">{title}</h2>
          {description ? <p className="mt-1 text-muted-sm">{description}</p> : null}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {actions}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            className="gap-1.5"
          >
            {isOpen ? "Collapse" : "Expand"}
            <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
          </Button>
        </div>
      </div>

      {isOpen ? <div className={cn("p-4", compact && "p-3", contentClassName)}>{children}</div> : null}
    </section>
  );
}
