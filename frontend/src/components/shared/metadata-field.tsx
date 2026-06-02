import type { LucideIcon } from "lucide-react";

interface MetadataFieldProps {
  icon: LucideIcon;
  label: string;
  children: React.ReactNode;
}

export function MetadataField({
  icon: Icon,
  label,
  children,
}: MetadataFieldProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-eyebrow">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div>{children}</div>
    </div>
  );
}
