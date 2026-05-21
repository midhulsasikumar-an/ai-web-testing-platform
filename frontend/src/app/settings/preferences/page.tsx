"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PreferencesSettingsPage() {
  return (
    <>
      <Header
        title="Preferences"
        description="Workspace preferences and local UI behavior."
      />
      <Card>
        <CardHeader>
          <CardTitle>Interface Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>The current app keeps UI preferences in the browser, not on the backend.</p>
          <p>Theme, density, and language controls can be added here when product requirements are finalized.</p>
        </CardContent>
      </Card>
    </>
  );
}
