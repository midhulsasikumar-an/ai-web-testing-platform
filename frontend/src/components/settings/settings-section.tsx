"use client";

import { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SettingsSectionProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function SettingsSection({
  title,
  description,
  icon,
  action,
  footer,
  children,
  className,
  contentClassName,
}: SettingsSectionProps) {
  return (
    <Card className={cn("", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          {icon ? (
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-primary">
              {icon}
            </div>
          ) : null}
          <div className="space-y-0.5">
            <CardTitle className="text-[15px]">{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </CardHeader>
      <CardContent className={cn("space-y-4", contentClassName)}>{children}</CardContent>
      {footer}
    </Card>
  );
}
