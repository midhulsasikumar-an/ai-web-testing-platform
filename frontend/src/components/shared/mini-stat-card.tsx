import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MiniStatCardProps {
  icon: LucideIcon;
  value: number | string;
  label: string;
  color: string;
  borderColor?: string;
}

const colorMap: Record<string, { bg: string; text: string; value: string }> = {
  blue: { bg: "bg-blue-50", text: "text-primary", value: "text-primary" },
  green: { bg: "bg-emerald-50", text: "text-emerald-600", value: "text-emerald-600" },
  red: { bg: "bg-red-50", text: "text-red-600", value: "text-red-600" },
  amber: { bg: "bg-amber-50", text: "text-amber-600", value: "text-amber-600" },
  purple: { bg: "bg-violet-50", text: "text-violet-600", value: "text-violet-600" },
  slate: { bg: "bg-slate-100", text: "text-slate-600", value: "text-slate-900" },
};

export function MiniStatCard({
  icon: Icon,
  value,
  label,
  color,
  borderColor,
}: MiniStatCardProps) {
  const tokens = colorMap[color] ?? colorMap.blue;

  return (
    <Card className={cn(borderColor)}>
      <CardContent className="flex items-center gap-3 py-3 px-4">
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", tokens.bg)}>
          <Icon className={cn("h-5 w-5", tokens.text)} />
        </div>
        <div>
          <p className={cn("text-2xl font-bold", tokens.value)}>{value}</p>
          <p className="text-[0.65rem] text-muted-foreground uppercase tracking-wider font-semibold">
            {label}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
