"use client";

import { useState } from "react";
import { Search, ChevronDown, Zap } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/utils";

export type WorkflowIntensity = "low" | "standard" | "aggressive" | "agent";

const WORKFLOWS: { id: WorkflowIntensity; label: string; desc: string }[] = [
  { id: "low", label: "Low", desc: "Passive reconnaissance only" },
  { id: "standard", label: "Standard", desc: "Shodan, Censys, scrape" },
  { id: "aggressive", label: "Aggressive", desc: "Full port scan + CyberNinja" },
  { id: "agent", label: "Agent Workflow", desc: "LangGraph multi-agent orchestration" },
];

interface OmnibarProps {
  onInvestigate: (target: string, intensity: WorkflowIntensity) => void;
  loading?: boolean;
}

export function Omnibar({ onInvestigate, loading }: OmnibarProps) {
  const [target, setTarget] = useState("");
  const [intensity, setIntensity] = useState<WorkflowIntensity>("standard");
  const [open, setOpen] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (target.trim()) onInvestigate(target.trim(), intensity);
  };

  const currentWorkflow = WORKFLOWS.find((w) => w.id === intensity);

  return (
    <form onSubmit={handleSubmit} className="flex-1 max-w-2xl mx-auto">
      <div className="flex rounded-xl border border-slate-700 bg-slate-900/80 shadow-lg shadow-black/20 overflow-hidden">
        <div className="flex-1 flex items-center gap-2 px-4 py-2.5">
          <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Email, Domain, IP, or Phone Number…"
            className="flex-1 bg-transparent text-slate-100 placeholder:text-slate-500 text-sm outline-none"
            disabled={loading}
          />
        </div>
        <DropdownMenu.Root open={open} onOpenChange={setOpen}>
          <DropdownMenu.Trigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2.5 border-l border-slate-700 hover:bg-slate-800/50 text-slate-300 text-sm transition-colors"
            >
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              <span>{currentWorkflow?.label}</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="min-w-[220px] rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-xl z-50"
              sideOffset={4}
            >
              {WORKFLOWS.map((w) => (
                <DropdownMenu.Item
                  key={w.id}
                  onSelect={() => {
                    setIntensity(w.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex flex-col gap-0.5 px-3 py-2 rounded-md cursor-pointer outline-none",
                    intensity === w.id ? "bg-cyan-500/15 text-cyan-400" : "text-slate-300 hover:bg-slate-800"
                  )}
                >
                  <span className="font-medium">{w.label}</span>
                  <span className="text-xs text-slate-500">{w.desc}</span>
                </DropdownMenu.Item>
              ))}
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
        <button
          type="submit"
          disabled={loading || !target.trim()}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          {loading ? "Investigating…" : "Investigate"}
        </button>
      </div>
    </form>
  );
}
