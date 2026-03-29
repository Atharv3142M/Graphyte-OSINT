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
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[60px] h-full glass-panel-dense flex flex-col items-center py-4 gap-1 border-r border-white/[0.06]">
      {/* Logo */}
      <div className="w-10 h-10 rounded-xl bg-cyan-500/15 flex items-center justify-center mb-2 glow-cyan-subtle">
        <ScanSearch className="w-4.5 h-4.5 text-cyan-400" />
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col items-center gap-1 w-full px-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon, href }) => {
          const isActive = pathname === href || (id === "dashboard" && pathname === "/");
          return (
            <Link
              key={id}
              href={href}
              className={cn(
                "w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200 group relative",
                isActive
                  ? "bg-cyan-500/15 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                  : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
              )}
            >
              <Icon className="w-5 h-5" />
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.6)]" />
              )}
              {/* Tooltip */}
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2.5 py-1.5 rounded-lg glass-panel text-xs text-slate-200 font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50">
                {label}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="text-[9px] text-slate-600 leading-none tracking-wide mt-2">v0.2</div>
    </aside>
  );
}
