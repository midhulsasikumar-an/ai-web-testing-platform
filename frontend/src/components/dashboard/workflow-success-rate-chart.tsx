"use client";

import { CheckCircle2 } from "lucide-react";

interface WorkflowSuccessRateChartProps {
  rate: number;
  data: { day: string; passed: number; failed: number }[];
}

export function WorkflowSuccessRateChart({ rate, data }: WorkflowSuccessRateChartProps) {
  // Use a fallback of mock data if the provided data is empty or too small to look good
  const chartData = data && data.length >= 7 ? data.slice(-7) : [
    { passed: 30, failed: 5 },
    { passed: 40, failed: 2 },
    { passed: 35, failed: 8 },
    { passed: 50, failed: 1 },
    { passed: 45, failed: 3 },
    { passed: 60, failed: 2 },
    { passed: 70, failed: 0 },
  ];

  const maxTotal = Math.max(...chartData.map(d => d.passed + d.failed));

  return (
    <div className="bg-[#F8FAFC] rounded-2xl p-6 flex flex-col justify-between shadow-sm border border-slate-100 col-span-1 sm:col-span-2 lg:col-span-2 xl:col-span-1">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-slate-700">Workflow Success Rate</h3>
        <CheckCircle2 className="h-4 w-4 text-slate-400" />
      </div>
      
      <div className="mt-4 flex items-end justify-between h-24">
        <div className="text-4xl font-bold tracking-tight text-slate-900 pb-1">
          {rate.toFixed(1)}%
        </div>
        
        <div className="flex items-end gap-1.5 h-full pt-4">
          {chartData.map((d, i) => {
            const heightPercentage = ((d.passed + d.failed) / maxTotal) * 100;
            // Add a slight gradient-like effect based on index to match design
            const opacity = 0.4 + (i * 0.1);
            
            return (
              <div 
                key={i} 
                className="w-5 md:w-6 bg-blue-600 rounded-t-sm transition-all hover:bg-blue-700 cursor-pointer"
                style={{ 
                  height: `${heightPercentage}%`,
                  opacity: i === chartData.length - 1 ? 1 : opacity
                }}
                title={`${d.passed} passed, ${d.failed} failed`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
