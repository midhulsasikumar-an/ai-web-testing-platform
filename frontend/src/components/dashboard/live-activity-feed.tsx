"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PlayCircle } from "lucide-react";
import { AILog } from "@/services/dashboard-api";

interface LiveActivityFeedProps {
  logs?: AILog[];
}

export function LiveActivityFeed({ logs = [] }: LiveActivityFeedProps) {
  const activities = Array.isArray(logs) && logs.length > 0 ? logs : [];

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <PlayCircle className="h-4 w-4 text-primary" />
          Live Testing Activity
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-2.5">
        {activities.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-slate-50 p-4 text-sm text-slate-500">No data available.</div>
        ) : (
          activities.map((activity: any, idx: number) => (
            <div
              key={activity.id ?? idx}
              className={`flex items-start gap-3 p-3 rounded-lg border ${activity.type === "error" ? "border-red-200 bg-red-50" : "border-border bg-slate-50/60"}`}
            >
              <div className="mt-0.5 shrink-0">
                {activity.icon ?? <PlayCircle className="h-4 w-4 text-slate-400" />}
              </div>
              <div className="min-w-0">
                <p className={`text-[13px] font-medium ${activity.type === "error" ? "text-red-700" : "text-slate-900"}`}>
                  {activity.title ?? String(activity.message ?? activity.title ?? "Activity")}
                </p>
                <p className="text-muted-sm mt-0.5">
                  {activity.subtitle ?? activity.subtitle_text ?? activity.time ?? ""}
                </p>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
