"use client";

import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Network,
  MapPin,
  Image,
  FileText,
  Shield,
} from "lucide-react";

export type NavItem = "dashboard" | "graph" | "spatial" | "media" | "reports" | "settings";

const NAV_ITEMS: { id: NavItem; label: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "graph", label: "Graph Explorer", icon: Network },
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
    <aside className="w-56 flex-none border-r border-slate-800 bg-slate-900/50 flex flex-col">
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
            <Network className="w-4 h-4 text-cyan-400" />
          </div>
          <span className="font-semibold text-slate-100 text-sm">OSINT Platform</span>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              active === id
                ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            )}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </button>
        ))}
      </nav>
      <div className="p-3 border-t border-slate-800">
        <div className="text-xs text-slate-500 px-3">v0.1.0 · Enterprise</div>
      </div>
    </aside>
  );
}
