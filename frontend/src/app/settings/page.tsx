"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/auth-context";
import {
  Bell, Shield, Palette, Globe, Database,
  Moon, Sun, Monitor, Check,
} from "lucide-react";
import { useState } from "react";

type ThemeOption = "system" | "light" | "dark";

const themeOptions: { id: ThemeOption; label: string; icon: React.ElementType }[] = [
  { id: "system", label: "System", icon: Monitor },
  { id: "light", label: "Light", icon: Sun },
  { id: "dark", label: "Dark", icon: Moon },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const [theme, setTheme] = useState<ThemeOption>("system");
  const [notifications, setNotifications] = useState({
    testComplete: true,
    bugDetected: true,
    weeklyReport: false,
    systemAlerts: true,
  });
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggleNotification = (key: keyof typeof notifications) => {
    setNotifications((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <>
      <Header title="Settings" description="Manage your application preferences and configuration." />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Settings */}
        <div className="lg:col-span-2 space-y-6">
          {/* Appearance */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Palette className="h-4 w-4 text-primary" />
                Appearance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Choose how SignalTrack looks on your device.
              </p>
              <div className="grid grid-cols-3 gap-3">
                {themeOptions.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTheme(id)}
                    className={`relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 ${
                      theme === id
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border bg-card hover:bg-accent/50 hover:border-border"
                    }`}
                  >
                    {theme === id && (
                      <div className="absolute top-2 right-2">
                        <Check className="h-3.5 w-3.5 text-primary" />
                      </div>
                    )}
                    <div className={`p-2 rounded-lg ${theme === id ? "bg-primary/10" : "bg-muted"}`}>
                      <Icon className={`h-5 w-5 ${theme === id ? "text-primary" : "text-muted-foreground"}`} />
                    </div>
                    <span className={`text-sm font-medium ${theme === id ? "text-foreground" : "text-muted-foreground"}`}>
                      {label}
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Bell className="h-4 w-4 text-primary" />
                Notifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {[
                { key: "testComplete" as const, label: "Test Completed", desc: "Get notified when a test run finishes" },
                { key: "bugDetected" as const, label: "Bug Detected", desc: "Alert when new bugs are found" },
                { key: "weeklyReport" as const, label: "Weekly Digest", desc: "Receive a summary of testing activity" },
                { key: "systemAlerts" as const, label: "System Alerts", desc: "Critical system status changes" },
              ].map(({ key, label, desc }) => (
                <div
                  key={key}
                  className="flex items-center justify-between py-3 px-1 rounded-lg hover:bg-accent/30 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-xs text-muted-foreground">{desc}</p>
                  </div>
                  <button
                    onClick={() => toggleNotification(key)}
                    className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
                      notifications[key] ? "bg-primary" : "bg-muted-foreground/30"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                        notifications[key] ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* API Configuration */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4 text-primary" />
                API Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Backend API URL
                </label>
                <Input
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="h-11 font-mono text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-muted-foreground">Connected to backend</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Security */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Session</span>
                <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full">Active</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Auth Method</span>
                <span className="text-xs text-muted-foreground">JWT Token</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Expires</span>
                <span className="text-xs text-muted-foreground">24 hours</span>
              </div>
            </CardContent>
          </Card>

          {/* Database Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                Database
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Provider</span>
                <span className="text-xs text-muted-foreground">MongoDB Atlas</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Database</span>
                <span className="text-xs font-mono text-muted-foreground">ai-web-testing</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Status</span>
                <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full">Connected</span>
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <Button onClick={handleSave} className="w-full h-11" disabled={saved}>
            {saved ? (
              <span className="flex items-center gap-2">
                <Check className="h-4 w-4" /> Saved
              </span>
            ) : (
              "Save Changes"
            )}
          </Button>
          <p className="text-xs text-center text-muted-foreground">
            Logged in as {user?.email}
          </p>
        </div>
      </div>
    </>
  );
}
