"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/auth-context";
import { useBugContext } from "@/context/bug-context";
import {
  User, Mail, Shield, Calendar, Activity,
  FlaskConical, Bug, CheckCircle2, Pencil,
  LogOut, Key,
} from "lucide-react";
import { useState } from "react";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const { stats } = useBugContext();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || "");

  const initials = user
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const activityItems = [
    { icon: FlaskConical, label: "Tests Run", value: stats.totalTests, color: "text-blue-500" },
    { icon: CheckCircle2, label: "Tests Passed", value: stats.passed, color: "text-green-500" },
    { icon: Bug, label: "Bugs Found", value: stats.openBugs, color: "text-red-500" },
    { icon: Activity, label: "Pass Rate", value: stats.totalTests > 0 ? `${Math.round((stats.passed / stats.totalTests) * 100)}%` : "N/A", color: "text-amber-500" },
  ];

  return (
    <>
      <Header title="Profile" description="View and manage your account details." />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Profile Card */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardContent className="pt-8 pb-6 flex flex-col items-center text-center">
              {/* Avatar */}
              <div className="relative mb-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 via-indigo-500 to-purple-600 text-white text-2xl font-bold shadow-lg shadow-indigo-500/20">
                  {initials}
                </div>
                <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-green-500 border-2 border-card">
                  <CheckCircle2 className="h-3.5 w-3.5 text-white" />
                </div>
              </div>
              <h2 className="text-lg font-bold">{user?.name || "User"}</h2>
              <p className="text-sm text-muted-foreground">{user?.email || ""}</p>
              <div className="flex items-center gap-1.5 mt-2">
                <span className="text-xs font-medium text-primary bg-primary/10 px-2.5 py-0.5 rounded-full">
                  QA Engineer
                </span>
              </div>
              <div className="w-full mt-6 pt-4 border-t border-border space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Role:</span>
                  <span className="ml-auto font-medium">Admin</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Joined:</span>
                  <span className="ml-auto font-medium">May 2026</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Auth:</span>
                  <span className="ml-auto font-medium text-green-600">Active</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-red-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-red-600">Danger Zone</CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                className="w-full"
                onClick={logout}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right side — Activity & Edit */}
        <div className="lg:col-span-2 space-y-6">
          {/* Activity Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {activityItems.map(({ icon: Icon, label, value, color }) => (
              <Card key={label}>
                <CardContent className="pt-5 pb-4 flex flex-col items-center text-center">
                  <div className={`p-2 rounded-lg bg-muted mb-2`}>
                    <Icon className={`h-5 w-5 ${color}`} />
                  </div>
                  <p className="text-xl font-bold">{value}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Edit Profile */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <User className="h-4 w-4 text-primary" />
                  Account Details
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing(!editing)}
                >
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  {editing ? "Cancel" : "Edit"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5" /> Full Name
                </label>
                {editing ? (
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="h-11"
                  />
                ) : (
                  <p className="text-sm font-medium py-2.5 px-3 rounded-lg bg-muted/50">
                    {user?.name || "—"}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" /> Email Address
                </label>
                <p className="text-sm font-medium py-2.5 px-3 rounded-lg bg-muted/50">
                  {user?.email || "—"}
                </p>
              </div>
              {editing && (
                <Button className="w-full h-11 mt-2" onClick={() => setEditing(false)}>
                  Save Changes
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Recent Sessions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Recent Sessions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { device: "Windows Desktop", ip: "192.168.1.4", time: "Active now", active: true },
                  { device: "Chrome Browser", ip: "192.168.1.4", time: "2 hours ago", active: false },
                ].map((session, i) => (
                  <div key={i} className="flex items-center justify-between py-2 px-1">
                    <div className="flex items-center gap-3">
                      <div className={`h-2 w-2 rounded-full ${session.active ? "bg-green-500 animate-pulse" : "bg-muted-foreground/40"}`} />
                      <div>
                        <p className="text-sm font-medium">{session.device}</p>
                        <p className="text-xs text-muted-foreground">{session.ip}</p>
                      </div>
                    </div>
                    <span className={`text-xs ${session.active ? "text-green-600 font-medium" : "text-muted-foreground"}`}>
                      {session.time}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
