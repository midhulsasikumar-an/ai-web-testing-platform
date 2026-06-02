import { cn } from "@/lib/utils";

interface AvatarCircleProps {
  name: string;
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses: Record<string, string> = {
  xs: "h-5 w-5 text-[0.5rem]",
  sm: "h-6 w-6 text-[0.55rem]",
  md: "h-7 w-7 text-[0.55rem]",
  lg: "h-8 w-8 text-xs",
};

const gradientByName = (name: string): string => {
  const gradients = [
    "from-blue-500 to-indigo-600",
    "from-violet-500 to-fuchsia-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-rose-500 to-pink-600",
    "from-sky-500 to-cyan-600",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  return gradients[Math.abs(hash) % gradients.length];
};

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
        "flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-white font-semibold ring-2 ring-white",
        gradientByName(name),
        sizeClasses[size],
        className,
      )}
    >
      {initials}
    </div>
  );
}
