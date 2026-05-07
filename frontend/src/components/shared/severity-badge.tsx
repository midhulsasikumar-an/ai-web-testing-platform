import { Badge } from "@/components/ui/badge";
import { severityColor } from "@/lib/constants";
import type { BugSeverity } from "@/types";

// ── Types ──────────────────────────────────────────────────────────

interface SeverityBadgeProps {
  severity: BugSeverity;
  className?: string;
}

// ── Component ──────────────────────────────────────────────────────

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <Badge variant="outline" className={`${severityColor(severity)} ${className ?? ""}`}>
      {severity}
    </Badge>
  );
}
