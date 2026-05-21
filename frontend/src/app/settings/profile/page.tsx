"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/auth-context";

export default function ProfileSettingsPage() {
  const { user } = useAuth();

  return (
    <>
      <Header
        title="Profile"
        description="Review the account profile currently restored from your authenticated session."
      />
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Name: {user?.name || "Unknown user"}</p>
          <p>Email: {user?.email || "No email available"}</p>
          <p>Role: {user?.role || "member"}</p>
          <p>Profile update endpoints are not exposed by the backend yet, so this page is currently read-only.</p>
        </CardContent>
      </Card>
    </>
  );
}
