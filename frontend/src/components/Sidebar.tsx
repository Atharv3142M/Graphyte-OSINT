"use client";

import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Network,
  ScanSearch,
  MapPin,
  Image,
  FileText,
  Shield,
} from "lucide-react";

export type NavItem = "dashboard" | "graph" | "recon" | "spatial" | "media" | "reports" | "settings";

const NAV_ITEMS: { id: NavItem; label: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "graph", label: "Graph Explorer", icon: Network },
  { id: "recon", label: "Recon Modules", icon: ScanSearch },
  { id: "spatial", label: "Spatial Intelligence", icon: MapPin },
  { id: "media", label: "Media Forensics", icon: Image },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "settings", label: "Secure Settings", icon: Shield },
];

interface SidebarProps {
  active: NavItem;
  onNavigate: (item: NavItem) => void;
}

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="w-[56px] h-full glass-panel-dense flex flex-col items-center py-3 gap-1">
      {/* Logo */}
      <div className="w-9 h-9 rounded-xl bg-cyan-500/15 flex items-center justify-center mb-4 glow-cyan-subtle">
        <Network className="w-4 h-4 text-cyan-400" />
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col items-center gap-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <div key={id} className="relative group">
            <button
              onClick={() => onNavigate(id)}
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200",
                active === id
                  ? "bg-cyan-500/15 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                  : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
              )}
            >
              <Icon className="w-[18px] h-[18px]" />
              {/* Active indicator dot */}
              {active === id && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.6)]" />
              )}
            </button>
            {/* Tooltip */}
            <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2.5 py-1.5 rounded-lg glass-panel text-xs text-slate-200 font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50">
              {label}
            </div>
          </div>
        ))}
      </nav>

      {/* Version */}
      <div className="text-[9px] text-slate-600 leading-none tracking-wide rotate-0 mt-2">v0.1</div>
    </aside>
  );
}
