"use client";

import { HelpCircle, Bell, Mail, Smartphone, MessageSquare, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function NotificationsSettingsPage() {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [toggles, setToggles] = useState({
    emailTestRun: true,
    emailBugs: true,
    emailWeekly: false,
    pushTestRun: true,
    pushBugs: true,
    slackAlerts: false
  });

  const toggle = (key: keyof typeof toggles) => {
    setToggles(prev => ({ ...prev, [key]: !prev[key] }));
  };

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
          <h2 className="text-3xl font-semibold tracking-tight text-[#131b2e]">Notifications</h2>
          <p className="text-sm text-[#434655] mt-1">Manage how and when you receive alerts.</p>
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
        
        {/* Email Notifications */}
        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Mail className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Email Notifications</h3>
              <p className="text-sm text-[#434655]">Sent to alex.rivera@testpilot.ai</p>
            </div>
          </div>
          <div className="p-6 space-y-6">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Test Run Completions</p>
                <p className="text-xs text-[#434655] mt-0.5">Get notified when a scheduled or manual test run finishes.</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.emailTestRun} onChange={() => toggle("emailTestRun")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.emailTestRun ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>
            
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Critical Bugs Detected</p>
                <p className="text-xs text-[#434655] mt-0.5">Receive immediate alerts for high-severity issues.</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.emailBugs} onChange={() => toggle("emailBugs")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.emailBugs ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Weekly Health Report</p>
                <p className="text-xs text-[#434655] mt-0.5">A digest of your workspace&apos;s AI health score and metrics.</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.emailWeekly} onChange={() => toggle("emailWeekly")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.emailWeekly ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>
          </div>
        </div>

        {/* Push Notifications */}
        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-indigo-50 rounded-lg">
              <Smartphone className="h-6 w-6 text-indigo-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Push Notifications</h3>
              <p className="text-sm text-[#434655]">Delivered directly to your device browser.</p>
            </div>
          </div>
          <div className="p-6 space-y-6">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Test Run Completions</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.pushTestRun} onChange={() => toggle("pushTestRun")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.pushTestRun ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>
            
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Critical Bugs Detected</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.pushBugs} onChange={() => toggle("pushBugs")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.pushBugs ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>
          </div>
        </div>

        {/* Integration Notifications */}
        <div className="bg-white/95 backdrop-blur-md border border-[#e2e8f0] shadow-sm rounded-xl overflow-hidden">
          <div className="p-6 border-b border-[#c3c6d7]/30 flex items-center gap-4">
            <div className="p-3 bg-[#4A154B]/10 rounded-lg">
              <MessageSquare className="h-6 w-6 text-[#4A154B]" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#131b2e]">Slack Alerts</h3>
              <p className="text-sm text-[#434655]">Send notifications to a connected Slack workspace.</p>
            </div>
          </div>
          <div className="p-6 space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm font-medium text-[#131b2e]">Enable Slack Integration</p>
                <p className="text-xs text-[#434655] mt-0.5">Post test results to #qa-alerts channel.</p>
              </div>
              <div className="relative inline-block w-10 h-5">
                <input type="checkbox" checked={toggles.slackAlerts} onChange={() => toggle("slackAlerts")} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 border-slate-200 appearance-none cursor-pointer transition-transform duration-200 ease-in-out z-10 checked:translate-x-5 checked:border-[#2563eb]" />
                <div className={`toggle-label block overflow-hidden h-5 rounded-full transition-colors duration-200 ease-in-out ${toggles.slackAlerts ? 'bg-[#2563eb]' : 'bg-slate-200'}`}></div>
              </div>
            </label>
            {toggles.slackAlerts && (
              <button className="text-sm font-semibold text-[#004ac6] hover:underline">
                Configure Webhook URL
              </button>
            )}
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
              {saving ? <><Bell className="h-4 w-4 animate-spin" /> Saving...</> : saved ? <><Check className="h-4 w-4" /> Saved</> : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
