"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntegrationsSettingsPage() {
  return (
    <>
      <Header
        title="Integrations"
        description="Connectors for external tools and services."
      />
      <Card>
        <CardHeader>
          <CardTitle>Connected Services</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>No integration management API is exposed yet.</p>
          <p>Use this route as the landing surface for future GitHub, Slack, and CI/CD connections.</p>
        </CardContent>
      </Card>
    </>
  );
}
