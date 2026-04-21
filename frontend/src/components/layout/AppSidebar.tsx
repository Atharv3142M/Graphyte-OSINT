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
  ShieldCheck,
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
    <aside className="w-[240px] h-full border-r border-slate-800 bg-slate-950/90 backdrop-blur-md flex flex-col">
      <div className="px-4 py-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md border border-cyan-800/60 bg-cyan-900/20 flex items-center justify-center">
            <ScanSearch className="w-4 h-4 text-cyan-300" />
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-200">OSINT Visualizer</p>
            <p className="text-[10px] text-slate-500">Analyst Workspace</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon, href }) => {
          const isActive = pathname === href || (id === "dashboard" && pathname === "/");
          return (
            <Link
              key={id}
              href={href}
              className={cn(
                "w-full rounded-md px-3 py-2.5 flex items-center gap-2 text-sm transition-colors",
                isActive
                  ? "bg-cyan-900/20 text-cyan-200 border border-cyan-700/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-slate-800">
        <div className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
          <div className="flex items-center gap-2 text-[11px] text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Secure Analyst Mode
          </div>
          <p className="text-[10px] text-slate-500 mt-1">v0.4-beta</p>
        </div>
      </div>
    </aside>
  );
}
