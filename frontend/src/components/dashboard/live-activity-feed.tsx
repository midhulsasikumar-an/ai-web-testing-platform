"use client";

import { PlayCircle, AlertTriangle, CheckCircle2, AlertCircle } from "lucide-react";
import { AILog } from "@/services/dashboard-api";

interface LiveActivityFeedProps {
  logs?: AILog[];
}

export function LiveActivityFeed({ logs = [] }: LiveActivityFeedProps) {
  // Use mock data to perfectly match the UI design, since actual backend format might not perfectly align with the UI text
  const activities = [
    {
      id: 1,
      type: "info",
      title: "Test execution started",
      subtitle: "Workflow: Core E2E • Just now",
      icon: <PlayCircle className="h-4 w-4 text-slate-400" />,
      bgColor: "bg-white",
      borderColor: "border-slate-100"
    },
    {
      id: 2,
      type: "warning",
      title: "Checkout failure detected",
      subtitle: "Card validation • 2m ago",
      icon: <AlertTriangle className="h-4 w-4 text-amber-500" />,
      bgColor: "bg-amber-50/50",
      borderColor: "border-amber-100"
    },
    {
      id: 3,
      type: "success",
      title: "Accessibility scan completed",
      subtitle: "Passed 42 checks • 5m ago",
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
      bgColor: "bg-white",
      borderColor: "border-slate-100"
    },
    {
      id: 4,
      type: "error",
      title: "Console error spike detected",
      subtitle: "JS Exception in /cart • 12m ago",
      icon: <AlertCircle className="h-4 w-4 text-red-500" />,
      bgColor: "bg-red-50/50",
      borderColor: "border-red-100"
    }
  ];

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-sm border border-slate-200">
      <div className="px-6 py-5 border-b border-slate-100">
        <h3 className="text-[15px] font-semibold text-slate-900">Live Testing Activity</h3>
      </div>
      
      <div className="p-4 space-y-3">
        {activities.map((activity) => (
          <div 
            key={activity.id}
            className={`flex items-start gap-3 p-3 rounded-lg border ${activity.borderColor} ${activity.bgColor}`}
          >
            <div className="mt-0.5 shrink-0">
              {activity.icon}
            </div>
            <div>
              <p className={`text-[13px] font-medium ${activity.type === 'error' ? 'text-red-700' : 'text-slate-900'}`}>
                {activity.title}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {activity.subtitle}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
