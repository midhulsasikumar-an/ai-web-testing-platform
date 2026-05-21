"use client";

import { TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIHealthWidgetProps {
  score: number;
}

export function AIHealthWidget({ score }: AIHealthWidgetProps) {
  // Calculate stroke dasharray for the SVG circle based on score
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-[#F8FAFC] rounded-2xl p-6 flex flex-col items-center justify-between col-span-1 shadow-sm border border-slate-100">
      <div className="w-full text-left">
        <h3 className="text-[13px] font-semibold text-slate-700">AI Health Score</h3>
      </div>
      
      <div className="relative flex items-center justify-center my-4">
        {/* SVG Circle Progress */}
        <svg className="transform -rotate-90 w-40 h-40">
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke="currentColor"
            strokeWidth="12"
            fill="transparent"
            className="text-blue-100"
          />
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke="currentColor"
            strokeWidth="12"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="text-blue-600 transition-all duration-1000 ease-in-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-slate-900 tracking-tight">{score}</span>
          <span className="text-sm font-semibold text-blue-600">%</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-blue-600 text-sm font-medium">
        <TrendingUp className="h-4 w-4" />
        <span>+2% from last week</span>
      </div>
    </div>
  );
}
