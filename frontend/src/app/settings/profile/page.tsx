"use client";

import { useAuth } from "@/context/auth-context";
import { HelpCircle, Bell, Edit2, Globe, Clock, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function ProfileSettingsPage() {
  const { user } = useAuth();
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
          <h2 className="text-3xl font-semibold tracking-tight text-[#131b2e]">Profile Settings</h2>
          <p className="text-sm text-[#434655] mt-1">Manage your personal information and workspace details.</p>
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

      <div className="max-w-[800px] mx-auto w-full px-10 py-8 flex-1">
        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden hover:border-[#c3c6d7] transition-colors">
          {/* Avatar Section */}
          <div className="p-8 border-b border-[#c3c6d7]/30 flex flex-col items-center">
            <div className="relative group cursor-pointer">
              <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-white shadow-lg bg-blue-100 flex items-center justify-center text-3xl font-bold text-blue-600">
                {user?.name?.charAt(0) || "A"}
              </div>
              <div className="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                <Edit2 className="h-8 w-8 text-white" />
              </div>
            </div>
            <div className="mt-4 text-center">
              <p className="text-2xl font-bold text-[#131b2e]">{user?.name || "Alex Rivera"}</p>
              <p className="text-sm text-[#434655]">{user?.role === "admin" ? "AI Systems Architect" : "Team Member"}</p>
            </div>
          </div>

          {/* Form Section */}
          <div className="p-8 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[#434655]">Full Name</label>
                <input 
                  type="text" 
                  defaultValue={user?.name || "Alex Rivera"}
                  className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all" 
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[#434655]">Email Address</label>
                <input 
                  type="email" 
                  defaultValue={user?.email || "alex.rivera@testpilot.ai"}
                  className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all" 
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[#434655]">Workspace Name</label>
              <input 
                type="text" 
                defaultValue="Acme Engineering Lab"
                className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all" 
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[#434655]">Short Bio</label>
              <textarea 
                defaultValue="AI Systems Architect focusing on autonomous quality pipelines."
                rows={4}
                className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all resize-none" 
              />
            </div>
          </div>

          {/* Profile Completion */}
          <div className="bg-[#f2f3ff] p-6 border-t border-[#c3c6d7]/30">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-semibold text-[#434655]">Profile completion</span>
              <span className="text-xs font-bold text-[#004ac6]">90%</span>
            </div>
            <div className="h-2 w-full bg-[#c3c6d7]/30 rounded-full overflow-hidden">
              <div className="h-full bg-[#2563eb] w-[90%] rounded-full shadow-[0_0_8px_rgba(37,99,235,0.4)]"></div>
            </div>
            <p className="mt-3 text-xs text-[#434655] italic text-center">Add a secondary email to reach 100%.</p>
          </div>
        </div>

        {/* Additional Settings Sections */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl p-6 flex items-start gap-4 hover:-translate-y-0.5 transition-transform">
            <div className="p-2 bg-[#39b8fd]/20 rounded-lg">
              <Globe className="h-6 w-6 text-[#004ac6]" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-[#131b2e]">Language</h4>
              <p className="text-sm text-[#434655] mt-0.5">English (United States)</p>
            </div>
          </div>
          <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl p-6 flex items-start gap-4 hover:-translate-y-0.5 transition-transform">
            <div className="p-2 bg-[#39b8fd]/20 rounded-lg">
              <Clock className="h-6 w-6 text-[#004ac6]" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-[#131b2e]">Timezone</h4>
              <p className="text-sm text-[#434655] mt-0.5">UTC-7 (Pacific Time)</p>
            </div>
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
              {saving ? (
                <>Saving...</>
              ) : saved ? (
                <><Check className="h-4 w-4" /> Saved</>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
