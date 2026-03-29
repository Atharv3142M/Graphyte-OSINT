"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Wrench,
  Network,
  FileText,
  ScanSearch,
  Settings,
} from "lucide-react";

const NAV_ITEMS: {
  id: string;
  label: string;
  icon: React.ElementType;
  href: string;
}[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { id: "tools", label: "Tools", icon: Wrench, href: "/tools" },
  { id: "workspace", label: "Workspace", icon: Network, href: "/workspace" },
  { id: "reports", label: "Reports", icon: FileText, href: "/reports" },
  { id: "settings", label: "Settings", icon: Settings, href: "/settings" },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[56px] h-full soc-panel-dense flex flex-col items-center py-3 gap-1 border-r border-slate-800">
      {/* Logo */}
      <div className="w-9 h-9 border border-cyan-900 bg-cyan-950/50 flex items-center justify-center mb-2">
        <ScanSearch className="w-4 h-4 text-cyan-500" />
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col items-center gap-0.5 w-full px-1.5">
        {NAV_ITEMS.map(({ id, label, icon: Icon, href }) => {
          const isActive = pathname === href || (id === "dashboard" && pathname === "/");
          return (
            <Link
              key={id}
              href={href}
              className={cn(
                "w-10 h-10 flex items-center justify-center transition-all duration-150 group relative",
                isActive
                  ? "bg-cyan-950/60 text-cyan-400 border border-cyan-900/50"
                  : "text-slate-600 hover:text-slate-400 hover:bg-white/[0.03]"
              )}
            >
              <Icon className="w-4 h-4" />
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-cyan-500" />
              )}
              {/* Tooltip */}
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2 py-1 soc-panel text-[10px] text-slate-300 font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50">
                {label}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="text-[8px] text-slate-700 leading-none tracking-wide mt-1">v0.3</div>
    </aside>
  );
}
