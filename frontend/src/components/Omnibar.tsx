"use client";

import { useState, type FormEvent } from "react";
import { Search, Loader2, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type WorkflowIntensity = "low" | "standard" | "aggressive" | "agent";

const INTENSITIES: { value: WorkflowIntensity; label: string; color: string }[] = [
  { value: "low", label: "Passive", color: "text-emerald-400" },
  { value: "standard", label: "Standard", color: "text-cyan-400" },
  { value: "aggressive", label: "Aggressive", color: "text-amber-400" },
  { value: "agent", label: "AI Agent", color: "text-violet-400" },
];

interface OmnibarProps {
  onInvestigate: (target: string, intensity: WorkflowIntensity) => void;
  loading: boolean;
}

export function Omnibar({ onInvestigate, loading }: OmnibarProps) {
  const [target, setTarget] = useState("");
  const [intensity, setIntensity] = useState<WorkflowIntensity>("standard");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const currentIntensity = INTENSITIES.find((i) => i.value === intensity)!;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const t = target.trim();
    if (!t) return;
    onInvestigate(t, intensity);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="glass-panel rounded-2xl flex items-center gap-2 px-4 py-2.5 transition-shadow focus-within:shadow-[0_0_24px_rgba(6,182,212,0.15)] focus-within:border-cyan-500/20">
        {/* Search icon */}
        <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />

        {/* Input */}
        <input
          type="text"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          placeholder="IP, domain, email, hash…"
          disabled={loading}
          className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-600 outline-none min-w-0"
        />

        {/* Intensity dropdown */}
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setDropdownOpen((v) => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 transition-colors"
          >
            <span className={currentIntensity.color}>{currentIntensity.label}</span>
            <ChevronDown className="w-3 h-3 text-slate-500" />
          </button>

          {dropdownOpen && (
            <div className="absolute top-full right-0 mt-2 glass-panel rounded-xl py-1 min-w-[120px] z-50 animate-fade-in-up">
              {INTENSITIES.map((i) => (
                <button
                  key={i.value}
                  type="button"
                  onClick={() => {
                    setIntensity(i.value);
                    setDropdownOpen(false);
                  }}
                  className={cn(
                    "w-full text-left px-3 py-2 text-xs font-medium hover:bg-white/5 transition-colors",
                    i.color,
                    intensity === i.value && "bg-white/5"
                  )}
                >
                  {i.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !target.trim()}
          className={cn(
            "flex-shrink-0 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all",
            loading
              ? "bg-slate-800 text-slate-500 cursor-wait"
              : "gradient-btn text-white hover:shadow-lg hover:shadow-cyan-500/20"
          )}
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            "Investigate"
          )}
        </button>
      </div>
    </form>
  );
}
