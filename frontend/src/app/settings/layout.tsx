"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Shield, Palette, Bell, HelpCircle, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const navItems = [
    { name: "Profile", href: "/settings/profile", icon: User },
    { name: "Security", href: "/settings/security", icon: Shield },
    { name: "Appearance", href: "/settings/appearance", icon: Palette },
    { name: "Notifications", href: "/settings/notifications", icon: Bell },
  ];

  return (
    <div className="bg-[#F8FAFC] min-h-[calc(100vh-4rem)] text-[#131b2e] flex flex-col md:flex-row -m-6 lg:-m-8">
      {/* Settings Sidebar */}
      <aside className="w-full md:w-64 bg-[#f2f3ff] border-r border-[#c3c6d7] flex flex-col p-4 gap-3 shrink-0 h-auto md:min-h-[calc(100vh-4rem)]">
        <div className="mb-8 px-3">
          <h1 className="text-2xl font-bold text-[#004ac6]">TestPilot AI</h1>
          <p className="text-sm font-medium text-[#434655] mt-1">Manage your workspace</p>
        </div>
        
        <nav className="flex-1 flex flex-col gap-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-4 px-4 py-3 rounded-lg transition-all font-medium text-sm",
                  isActive 
                    ? "bg-[#39b8fd]/10 text-[#004ac6] font-semibold" 
                    : "text-[#434655] hover:text-[#131b2e] hover:bg-[#e2e7ff]"
                )}
              >
                <Icon className="h-5 w-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto flex flex-col gap-1 border-t border-[#c3c6d7]/30 pt-4">
          <button className="w-full text-left flex items-center gap-4 px-4 py-3 text-[#434655] hover:bg-[#e2e7ff] transition-all rounded-lg text-sm font-medium">
            <HelpCircle className="h-5 w-5" />
            Support
          </button>
          <button className="w-full text-left flex items-center gap-4 px-4 py-3 text-[#434655] hover:bg-[#e2e7ff] transition-all rounded-lg text-sm font-medium">
            <LogOut className="h-5 w-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Settings Content Area */}
      <main className="flex-1 flex flex-col w-full overflow-hidden bg-[#faf8ff]">
        {children}
      </main>
    </div>
  );
}
