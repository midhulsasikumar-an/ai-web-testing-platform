import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────

interface MiniStatCardProps {
  /** Icon displayed in the colored container */
  icon: LucideIcon;
  /** Numeric or string value */
  value: number | string;
  /** Short label below the value */
  label: string;
  /** Tailwind color class for the icon bg/text (e.g. "blue", "green", "red", "amber") */
  color: string;
  /** Optional border accent class */
  borderColor?: string;
}

// ── Component ──────────────────────────────────────────────────────

export function MiniStatCard({
  icon: Icon,
  value,
  label,
  color,
  borderColor,
}: MiniStatCardProps) {
  return (
    <Card className={cn(borderColor)}>
      <CardContent className="flex items-center gap-3 py-3 px-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg bg-${color}-50`}
        >
          <Icon className={`h-5 w-5 text-${color}-500`} />
        </div>
        <div>
          <p className={`text-2xl font-bold text-${color}-600`}>{value}</p>
          <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">
            {label}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
