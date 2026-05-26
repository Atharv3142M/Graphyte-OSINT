"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  Activity,
  Compass,
  FlaskConical,
  Share2,
  FileText,
  Settings,
  Radar,
} from "lucide-react";

const NAV_ITEMS: {
  id: string;
  label: string;
  caption: string;
  icon: React.ElementType;
  href: string;
  advanced?: boolean;
}[] = [
  { id: "dashboard", label: "Search", caption: "Investigate any target", icon: Compass, href: "/dashboard" },
  { id: "reports", label: "Reports", caption: "Export outputs", icon: FileText, href: "/reports" },
  { id: "settings", label: "Settings", caption: "Keys and services", icon: Settings, href: "/settings" },
  { id: "tools", label: "Module Runner", caption: "Run a single module", icon: FlaskConical, href: "/tools", advanced: true },
  { id: "workspace", label: "Workspace", caption: "Graph + terminal", icon: Share2, href: "/workspace", advanced: true },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[280px] h-full border-r border-white/[0.05] bg-white/[0.01] backdrop-blur-xl flex flex-col">
      <div className="px-5 py-5 border-b border-white/[0.05]">
          <div className="flex items-center gap-3 w-full pl-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.5)]">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <p className="text-sm font-bold tracking-tight text-slate-100">Graphyte OSINT</p>
              <p className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Target Intel</p>
            </div>
          </div>
      </div>

      <nav className="flex-1 p-3.5 space-y-1">
        {NAV_ITEMS.map(({ id, label, caption, icon: Icon, href, advanced }, idx) => {
          const isActive = pathname === href || (id === "dashboard" && pathname === "/");
          const prevIsAdvanced = idx > 0 ? !!NAV_ITEMS[idx - 1].advanced : false;
          const showDivider = !!advanced && !prevIsAdvanced;
          return (
            <div key={id}>
              {showDivider ? (
                <div className="px-3 pt-4 pb-2 text-[10px] uppercase tracking-widest text-slate-600 font-mono">
                  Advanced
                </div>
              ) : null}
              <Link
                href={href}
                className={cn(
                  "w-full rounded-xl px-3 py-2.5 flex items-center gap-3 transition-all border",
                  isActive
                    ? "bg-indigo-500/10 text-indigo-100 border-indigo-500/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]"
                    : "text-slate-400 border-transparent hover:text-slate-100 hover:bg-white/[0.04] hover:shadow-[inset_0_1px_1px_rgba(255,255,255,0.02)]",
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium leading-tight flex items-center gap-1.5">
                    {label}
                  </div>
                  <div className="text-[11px] text-slate-500 truncate">{caption}</div>
                </div>
              </Link>
            </div>
          );
        })}
      </nav>

      <div className="p-3.5 border-t border-slate-800">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2.5">
          <div className="text-[11px] text-slate-300">Open-source edition</div>
          <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
            Unified module orchestration, STIX graphing, and export workflows.
          </p>
          <p className="text-[10px] text-slate-600 mt-1.5 font-mono">build 2026.04</p>
        </div>
      </div>
    </aside>
  );
}
