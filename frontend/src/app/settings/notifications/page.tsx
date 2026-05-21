"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotificationsSettingsPage() {
  return (
    <>
      <Header
        title="Notifications"
        description="Delivery preferences for alerts and updates."
      />
      <Card>
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Email, digest, and webhook notification options are not wired to backend persistence yet.</p>
          <p>This page exists so route validation and navigation no longer fail.</p>
        </CardContent>
      </Card>
    </>
  );
}
