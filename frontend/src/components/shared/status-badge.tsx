import { Badge } from "@/components/ui/badge";
import { statusColor } from "@/lib/constants";
import type { BugStatus } from "@/types";

// ── Types ──────────────────────────────────────────────────────────

interface StatusBadgeProps {
  status: BugStatus;
  className?: string;
}

// ── Component ──────────────────────────────────────────────────────

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge variant="secondary" className={`${statusColor(status)} ${className ?? ""}`}>
      {status}
    </Badge>
  );
}
