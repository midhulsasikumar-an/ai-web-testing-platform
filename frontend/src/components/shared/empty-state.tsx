import type { LucideIcon } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface EmptyStateProps {
  /** Icon displayed in the empty state */
  icon: LucideIcon;
  /** Primary message */
  title: string;
  /** Optional secondary description */
  description?: string;
}

// ── Component ──────────────────────────────────────────────────────

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="py-12 text-center text-muted-foreground">
      <Icon className="h-8 w-8 mx-auto mb-3 opacity-40" />
      <p className="font-medium">{title}</p>
      {description && (
        <p className="text-sm mt-1">{description}</p>
      )}
    </div>
  );
}
