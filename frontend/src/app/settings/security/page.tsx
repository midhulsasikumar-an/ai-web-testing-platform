"use client";

import { HelpCircle, Bell, Shield, Key, Smartphone, Laptop, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function SecuritySettingsPage() {
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
          <h2 className="text-3xl font-semibold tracking-tight text-[#131b2e]">Security</h2>
          <p className="text-sm text-[#434655] mt-1">Manage passwords, 2FA, and your active sessions.</p>
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
            <div className="p-3 bg-blue-50 rounded-lg">
              <Key className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Change Password</h3>
              <p className="text-sm text-[#434655]">Update your password associated with your account.</p>
            </div>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[#434655]">Current Password</label>
              <input type="password" placeholder="••••••••" className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all max-w-md" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[#434655]">New Password</label>
              <input type="password" placeholder="••••••••" className="px-4 py-2.5 rounded-lg border border-[#c3c6d7] bg-white text-base focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all max-w-md" />
            </div>
          </div>
        </div>

        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-purple-50 rounded-lg">
              <Smartphone className="h-6 w-6 text-purple-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-[#131b2e]">Two-Factor Authentication (2FA)</h3>
              <p className="text-sm text-[#434655]">Add an extra layer of security to your account.</p>
            </div>
            <button className="px-4 py-2 bg-[#2563eb] text-white text-sm font-medium rounded-lg hover:bg-[#004ac6] transition-colors">
              Enable 2FA
            </button>
          </div>
        </div>

        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-amber-50 rounded-lg">
              <Laptop className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Active Sessions</h3>
              <p className="text-sm text-[#434655]">Manage the devices currently logged into your account.</p>
            </div>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between p-4 border border-[#c3c6d7]/50 rounded-lg bg-[#f2f3ff]">
              <div>
                <p className="text-sm font-semibold text-[#131b2e]">Windows PC - Chrome</p>
                <p className="text-xs text-[#434655]">San Francisco, CA • Current session</p>
              </div>
              <span className="text-xs font-bold text-green-600 bg-green-100 px-2 py-1 rounded">Active</span>
            </div>
            <div className="flex items-center justify-between p-4 border border-[#c3c6d7]/50 rounded-lg">
              <div>
                <p className="text-sm font-semibold text-[#131b2e]">iPhone 13 - Safari</p>
                <p className="text-xs text-[#434655]">San Francisco, CA • Last active 2h ago</p>
              </div>
              <button className="text-sm text-red-600 font-medium hover:underline">Revoke</button>
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
              {saving ? <><Shield className="h-4 w-4 animate-spin" /> Saving...</> : saved ? <><Check className="h-4 w-4" /> Saved</> : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
