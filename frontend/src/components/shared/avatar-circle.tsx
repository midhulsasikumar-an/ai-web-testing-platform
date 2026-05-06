import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────

interface AvatarCircleProps {
  /** Full name to extract initials from */
  name: string;
  /** Size variant */
  size?: "xs" | "sm" | "md" | "lg";
  /** Additional className */
  className?: string;
}

// ── Size map ───────────────────────────────────────────────────────

const sizeClasses: Record<string, string> = {
  xs: "h-5 w-5 text-[0.5rem]",
  sm: "h-6 w-6 text-[0.55rem]",
  md: "h-7 w-7 text-[0.55rem]",
  lg: "h-8 w-8 text-xs",
};

// ── Component ──────────────────────────────────────────────────────

export function AvatarCircle({
  name,
  size = "md",
  className,
}: AvatarCircleProps) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("");

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 text-white font-bold",
        sizeClasses[size],
        className
      )}
    >
      {initials}
    </div>
  );
}
