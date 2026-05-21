"use client";

import { Bell, Search, HelpCircle, Grid } from "lucide-react";
import { useAuth } from "@/context/auth-context";

interface HeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function Header({ title, children }: HeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-200 mb-6 bg-white px-8 pt-8 -mt-8 -mx-8">
      <div className="flex items-center gap-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 w-48 leading-tight">
          {title.split(' ').map((word, i) => (
            <span key={i}>{word}{i === 1 ? <br/> : ' '}</span>
          ))}
        </h1>
        
        <div className="hidden md:flex items-center gap-4 text-[13px] font-medium text-slate-600">
          <a href="#" className="hover:text-slate-900 transition-colors">Docs</a>
          <a href="#" className="hover:text-slate-900 transition-colors">API</a>
          <a href="#" className="hover:text-slate-900 transition-colors">Support</a>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {children}
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search tests..." 
            className="h-9 w-64 rounded-full border border-slate-300 pl-9 pr-4 text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
        </div>

        <button className="h-9 px-4 rounded-md border border-slate-300 bg-white text-slate-700 text-[13px] font-medium hover:bg-slate-50 transition-colors whitespace-nowrap">
          Generate<br className="hidden" /> Workflow
        </button>
        
        <button className="h-9 px-4 rounded-md bg-blue-600 text-white text-[13px] font-medium hover:bg-blue-700 transition-colors shadow-sm whitespace-nowrap">
          Run<br className="hidden" /> AI Test
        </button>

        <div className="flex items-center gap-3 pl-2">
          <button className="relative text-slate-500 hover:text-slate-900 transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute 1 top-0 right-0 h-1.5 w-1.5 rounded-full bg-red-500 ring-2 ring-white"></span>
          </button>
          <button className="text-slate-500 hover:text-slate-900 transition-colors">
            <HelpCircle className="h-5 w-5" />
          </button>
          <button className="text-slate-500 hover:text-slate-900 transition-colors">
            <Grid className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
