"use client";

import { RecentTest } from "@/services/dashboard-api";
import { Eye, ArrowRight, CheckCircle2, AlertCircle, AlertTriangle, Monitor, Smartphone, Globe, Shield } from "lucide-react";
import Link from "next/link";

interface LatestTestRunsTableProps {
  tests: RecentTest[];
}

// Map the generic icon types from the image
const getIconForProject = (project: string) => {
  if (project.includes('mobile') || project.includes('m.')) return <Smartphone className="h-4 w-4 text-slate-400" />;
  if (project.includes('api')) return <Monitor className="h-4 w-4 text-slate-400" />;
  if (project.includes('auth') || project.includes('portal')) return <Globe className="h-4 w-4 text-slate-400" />;
  if (project.includes('staging')) return <Shield className="h-4 w-4 text-slate-400" />;
  return <Globe className="h-4 w-4 text-slate-400" />;
};

const getStatusBadge = (status: string) => {
  const s = status.toLowerCase();
  if (s === 'passed' || s === 'completed' || s === 'success') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
        <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Completed</span>
      </div>
    );
  }
  if (s === 'failed' || s === 'error') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 border border-red-200">
        <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
        <span className="text-[10px] font-bold text-red-700 uppercase tracking-wider">Failed</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200">
      <div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
      <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Warning</span>
    </div>
  );
};

export function LatestTestRunsTable({ tests }: LatestTestRunsTableProps) {
  // Use backend tests but augment with missing UI design fields like "duration", "bugs", and nice titles
  // In a real scenario, this would just render `tests` directly if the backend is updated.
  const displayTests = tests.length > 0 ? tests : [
    {
      test_id: "1", project: "acme-store.com", url: "acme-store.com", 
      test_type: "Core Checkout Flow", overall_status: "passed", health_score: 100, date: "Just now", bugs: 0, duration: "4m 12s"
    },
    {
      test_id: "2", project: "m.acme-shop.io", url: "m.acme-shop.io", 
      test_type: "Mobile UI Scan", overall_status: "failed", health_score: 65, date: "15m ago", bugs: 3, duration: "2m 45s"
    },
    {
      test_id: "3", project: "api.acme.com", url: "api.acme.com", 
      test_type: "API Endpoint Load", overall_status: "passed", health_score: 98, date: "1h ago", bugs: 0, duration: "52s"
    },
    {
      test_id: "4", project: "portal.acme.dev", url: "portal.acme.dev", 
      test_type: "Auth Integration", overall_status: "passed", health_score: 92, date: "2h ago", bugs: 0, duration: "1m 20s"
    },
    {
      test_id: "5", project: "staging-env.io", url: "staging-env.io", 
      test_type: "Full Regression", overall_status: "warning", health_score: 84, date: "4h ago", bugs: 1, duration: "12m 30s"
    }
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
        <h3 className="text-[17px] font-semibold text-slate-900">Latest Test Runs</h3>
        <Link href="/test-history" className="text-[13px] font-medium text-blue-600 flex items-center gap-1 hover:text-blue-700 transition-colors">
          View All History
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Website</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Test Type</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider text-center">Bugs</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Stability</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Duration</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider">Last Run</th>
              <th className="px-6 py-4 text-[12px] font-semibold text-slate-500 uppercase tracking-wider text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {displayTests.map((test, index) => (
              <tr key={test.test_id || index} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50/50 border border-blue-100/50">
                      {getIconForProject(test.project || test.url)}
                    </div>
                    <span className="text-[13px] font-medium text-slate-900">{test.project || test.url}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-[13px] text-slate-600">{test.test_type}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(test.overall_status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className={`text-[13px] font-bold ${(test as RecentTest & { bugs?: number }).bugs ? 'text-red-500' : 'text-slate-600'}`}>
                    {(test as RecentTest & { bugs?: number }).bugs || 0}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${test.health_score > 90 ? 'bg-blue-600' : test.health_score > 70 ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${test.health_score}%` }}
                      ></div>
                    </div>
                    <span className={`text-[12px] font-bold ${test.health_score > 90 ? 'text-blue-600' : test.health_score > 70 ? 'text-amber-500' : 'text-red-500'}`}>
                      {test.health_score}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-[13px] text-slate-600">{(test as RecentTest & { duration?: string }).duration || "1m 30s"}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-[13px] text-slate-600">{test.date}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <button className="text-slate-400 hover:text-slate-900 transition-colors">
                    <Eye className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
