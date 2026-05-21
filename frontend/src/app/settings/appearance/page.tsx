"use client";

import { HelpCircle, Bell, Palette, Monitor, Moon, Sun, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function AppearanceSettingsPage() {
  const [theme, setTheme] = useState("system");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }, 1000);
  };

  return (
    <div className="flex flex-col min-h-full pb-32">
      <header className="sticky top-0 z-30 bg-[#faf8ff]/80 backdrop-blur-md px-10 py-6 flex justify-between items-center border-b border-[#e2e8f0]">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-[#131b2e]">Appearance</h2>
          <p className="text-sm text-[#434655] mt-1">Customize the look and feel of your workspace.</p>
        </div>
        <div className="flex items-center gap-4">
          <button className="p-2 rounded-lg hover:bg-[#f2f3ff] transition-all text-[#434655]">
            <HelpCircle className="h-6 w-6" />
          </button>
          <button className="p-2 rounded-lg hover:bg-[#f2f3ff] transition-all text-[#434655]">
            <Bell className="h-6 w-6" />
          </button>
        </div>
      </header>

      <div className="max-w-[800px] mx-auto w-full px-10 py-8 flex-1 space-y-6">
        
        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-pink-50 rounded-lg">
              <Palette className="h-6 w-6 text-pink-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Theme Preferences</h3>
              <p className="text-sm text-[#434655]">Select your preferred interface theme.</p>
            </div>
          </div>
          
          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* System */}
            <button 
              onClick={() => setTheme("system")}
              className={cn("p-4 border rounded-xl flex flex-col items-center gap-3 transition-all", theme === "system" ? "border-blue-500 bg-blue-50/50" : "border-[#c3c6d7] hover:bg-[#f2f3ff]")}
            >
              <div className="h-20 w-32 bg-gradient-to-br from-slate-100 to-slate-800 rounded-lg border border-slate-200 shadow-sm flex items-center justify-center">
                <Monitor className="h-8 w-8 text-slate-500" />
              </div>
              <span className="text-sm font-medium text-[#131b2e]">System match</span>
            </button>

            {/* Light */}
            <button 
              onClick={() => setTheme("light")}
              className={cn("p-4 border rounded-xl flex flex-col items-center gap-3 transition-all", theme === "light" ? "border-blue-500 bg-blue-50/50" : "border-[#c3c6d7] hover:bg-[#f2f3ff]")}
            >
              <div className="h-20 w-32 bg-slate-50 rounded-lg border border-slate-200 shadow-sm flex items-center justify-center">
                <Sun className="h-8 w-8 text-amber-500" />
              </div>
              <span className="text-sm font-medium text-[#131b2e]">Light mode</span>
            </button>

            {/* Dark */}
            <button 
              onClick={() => setTheme("dark")}
              className={cn("p-4 border rounded-xl flex flex-col items-center gap-3 transition-all", theme === "dark" ? "border-blue-500 bg-blue-50/50" : "border-[#c3c6d7] hover:bg-[#f2f3ff]")}
            >
              <div className="h-20 w-32 bg-slate-900 rounded-lg border border-slate-700 shadow-sm flex items-center justify-center">
                <Moon className="h-8 w-8 text-blue-300" />
              </div>
              <span className="text-sm font-medium text-[#131b2e]">Dark mode</span>
            </button>
          </div>
        </div>

      </div>

      {/* Sticky Action Bar */}
      <div className="fixed bottom-0 right-0 left-0 md:left-64 bg-[#faf8ff]/90 backdrop-blur-xl border-t border-[#c3c6d7]/30 px-10 py-4 z-40">
        <div className="max-w-[800px] mx-auto flex justify-between items-center w-full lg:-ml-[calc(50vw-400px)] 2xl:ml-auto">
          <p className="text-sm font-medium text-[#434655]">Unsaved changes will be lost if you leave.</p>
          <div className="flex items-center gap-4">
            <button className="px-6 py-2 text-sm font-medium text-[#434655] hover:bg-[#f2f3ff] rounded-lg transition-all">
              Discard
            </button>
            <button 
              onClick={handleSave}
              disabled={saving}
              className={cn(
                "px-8 py-2.5 rounded-lg text-sm font-medium shadow-lg transition-all flex items-center justify-center gap-2 min-w-[140px]",
                saved ? "bg-green-600 text-white shadow-green-600/20" : "bg-[#2563eb] text-white shadow-[#2563eb]/20 active:scale-95 hover:bg-[#004ac6]"
              )}
            >
              {saving ? <><Palette className="h-4 w-4 animate-spin" /> Saving...</> : saved ? <><Check className="h-4 w-4" /> Saved</> : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
