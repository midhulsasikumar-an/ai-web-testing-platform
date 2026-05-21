"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const sections = [
    { href: "/settings/profile", title: "Profile", description: "View your authenticated account details." },
    { href: "/settings/security", title: "Security", description: "Review JWT session handling and access controls." },
    { href: "/settings/preferences", title: "Preferences", description: "Adjust local UI and workspace preferences." },
    { href: "/settings/notifications", title: "Notifications", description: "Configure alerts and delivery channels." },
    { href: "/settings/integrations", title: "Integrations", description: "Manage external tool connections." },
  ];

  return (
    <>
      <Header
        title="Settings"
        description="Manage account, security, and workspace preferences."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sections.map((section) => (
          <Card key={section.href}>
            <CardContent className="p-6 space-y-4">
              <div>
                <h2 className="font-semibold text-base">{section.title}</h2>
                <p className="text-sm text-muted-foreground mt-1">{section.description}</p>
              </div>
              <Link href={section.href} className={cn(buttonVariants({ variant: "outline" }))}>
                Open
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
