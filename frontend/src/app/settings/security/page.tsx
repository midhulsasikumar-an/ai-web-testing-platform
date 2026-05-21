"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SecuritySettingsPage() {
  return (
    <>
      <Header
        title="Security"
        description="Security controls for JWT sessions and account access."
      />
      <Card>
        <CardHeader>
          <CardTitle>Session Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>JWT sessions are stored in the browser and validated on app startup.</p>
          <p>Logout clears the local session and redirects back to the login flow.</p>
          <p>Backend password reset and MFA endpoints are not implemented yet.</p>
        </CardContent>
      </Card>
    </>
  );
}
