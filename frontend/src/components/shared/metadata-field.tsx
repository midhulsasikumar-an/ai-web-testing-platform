import type { LucideIcon } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface MetadataFieldProps {
  /** Icon shown next to the label */
  icon: LucideIcon;
  /** Uppercase label text */
  label: string;
  /** Content to display as the value */
  children: React.ReactNode;
}

// ── Component ──────────────────────────────────────────────────────

export function MetadataField({
  icon: Icon,
  label,
  children,
}: MetadataFieldProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div>{children}</div>
    </div>
  );
}
