"use client";

import { useState, type FormEvent } from "react";
import { Search, Loader2, ChevronDown, X, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { classify, normalizeInput, type DetectedType } from "@/lib/classifier";

export type WorkflowIntensity = "low" | "standard" | "aggressive" | "agent";

const INTENSITIES: { value: WorkflowIntensity; label: string; color: string }[] = [
  { value: "low", label: "Passive", color: "text-emerald-400" },
  { value: "standard", label: "Standard", color: "text-cyan-400" },
  { value: "aggressive", label: "Aggressive", color: "text-amber-400" },
  { value: "agent", label: "AI Agent", color: "text-violet-400" },
];

/* ── Type label + color map ─────────────────────────────── */

const TYPE_META: Record<DetectedType, { label: string; bg: string; text: string; border: string }> = {
  ipv4:       { label: "IPv4",        bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  ipv6:       { label: "IPv6",        bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  cidr:       { label: "CIDR",        bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  domain:     { label: "Domain",      bg: "bg-violet-500/10", text: "text-violet-400", border: "border-violet-500/30" },
  url:        { label: "URL",         bg: "bg-blue-500/10",   text: "text-blue-400",   border: "border-blue-500/30"   },
  email:      { label: "Email",       bg: "bg-amber-500/10",  text: "text-amber-400",  border: "border-amber-500/30"  },
  username:   { label: "Username",   bg: "bg-pink-500/10",  text: "text-pink-400",   border: "border-pink-500/30"   },
  hash_md5:   { label: "MD5",         bg: "bg-orange-500/10",text: "text-orange-400",border: "border-orange-500/30" },
  hash_sha1:  { label: "SHA-1",       bg: "bg-orange-500/10",text: "text-orange-400",border: "border-orange-500/30" },
  hash_sha256:{ label: "SHA-256",     bg: "bg-orange-500/10",text: "text-orange-400",border: "border-orange-500/30" },
  phone:      { label: "Phone",      bg: "bg-teal-500/10",   text: "text-teal-400",   border: "border-teal-500/30"   },
  asn:        { label: "ASN",        bg: "bg-cyan-500/10",   text: "text-cyan-400",   border: "border-cyan-500/30"   },
  company:    { label: "Company",    bg: "bg-slate-500/10",  text: "text-slate-400",  border: "border-slate-500/30" },
};

interface OmnibarProps {
  onResult?: (payload: {
    playbookId: string;
    target: string;
    types: string[];
    modules: string[];
    moduleLabels: Record<string, string>;
  }) => void;
  loading: boolean;
  onLoadingChange?: (v: boolean) => void;
}

/**
 * Smart search bar — classifies input into OSINT types and fans out
 * to all relevant modules via POST /api/investigate.
 */
export function Omnibar({ onResult, loading, onLoadingChange }: OmnibarProps) {
  const [target, setTarget] = useState("");
  const [intensity, setIntensity] = useState<WorkflowIntensity>("standard");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeTypes, setActiveTypes] = useState<DetectedType[]>([]);
  const [showAmbiguity, setShowAmbiguity] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentIntensity = INTENSITIES.find((i) => i.value === intensity)!;

  /* ── Run classifier on every keystroke ────────────────── */
  const handleChange = (val: string) => {
    setTarget(val);
    setError(null);
    if (!val.trim()) {
      setActiveTypes([]);
      setShowAmbiguity(false);
      return;
    }
    const types = classify(val);
    setActiveTypes(types);
    // Only show ambiguity when username is one of multiple types
    setShowAmbiguity(types.length > 1);
  };

  /* ── Toggle a specific type in/out of the active set ─────── */
  const toggleType = (t: DetectedType) => {
    setActiveTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  /* ── Submit: POST to /api/investigate with target + types ─── */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const normalized = normalizeInput(target.trim());
    if (!normalized) return;

    const typesToSend = activeTypes.length > 0 ? activeTypes : classify(target);

    onLoadingChange?.(true);
    setError(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/investigate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Tenant-ID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
          },
          body: JSON.stringify({ target: normalized, types: typesToSend }),
        }
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail ?? `Request failed with ${res.status}`);
      }

      const data = await res.json() as {
        playbook_id: string;
        target: string;
        types: string[];
        modules: string[];
        module_labels: Record<string, string>;
      };
      setTarget("");
      setActiveTypes([]);
      setShowAmbiguity(false);
      onResult?.({
        playbookId: data.playbook_id,
        target: data.target,
        types: data.types,
        modules: data.modules,
        moduleLabels: data.module_labels ?? {},
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Investigation failed");
    } finally {
      onLoadingChange?.(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      {/* ── Main bar ── */}
      <div
        className={cn(
          "soc-panel rounded-md flex items-center gap-2 px-3 py-2 transition-all",
          "focus-within:border-slate-500",
          error && "border-red-500/50"
        )}
      >
        <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />

        <input
          type="text"
          value={target}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="IP, domain, email, hash, username…"
          disabled={loading}
          className="flex-1 bg-transparent text-sm text-slate-200 placeholder:text-slate-600 outline-none min-w-0 font-mono"
        />

        {/* Ambiguity help icon */}
        {activeTypes.length > 0 && (
          <button
            type="button"
            onClick={() => setShowAmbiguity((v) => !v)}
            className="flex-shrink-0 text-slate-600 hover:text-cyan-500 transition-colors"
            title="Toggle type detection"
          >
            <HelpCircle className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Intensity selector */}
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setDropdownOpen((v) => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-slate-800 bg-slate-900 hover:bg-slate-800 text-xs font-mono transition-colors"
          >
            <span className={currentIntensity.color}>{currentIntensity.label}</span>
            <ChevronDown className="w-3 h-3 text-slate-500" />
          </button>

          {dropdownOpen && (
            <div className="absolute top-full right-0 mt-1 soc-panel-dense rounded-sm py-1 min-w-[120px] z-50 animate-fade-in-up">
              {INTENSITIES.map((i) => (
                <button
                  key={i.value}
                  type="button"
                  onClick={() => { setIntensity(i.value); setDropdownOpen(false); }}
                  className={cn(
                    "w-full text-left px-3 py-2 text-xs font-mono hover:bg-slate-800 transition-colors",
                    i.color,
                    intensity === i.value && "bg-slate-800"
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
            "flex-shrink-0 px-4 py-1.5 rounded-sm text-xs font-mono tracking-widest uppercase transition-all",
            loading
              ? "bg-slate-800 text-slate-500 border border-slate-700 cursor-wait"
              : "soc-btn-primary"
          )}
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            "Scan"
          )}
        </button>
      </div>

      {/* ── Error message ── */}
      {error && (
        <div className="mt-1.5 px-3 py-1.5 rounded-lg bg-red-950/40 border border-red-900/50 text-xs text-red-400 font-mono flex items-center gap-2">
          <X className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* ── Type pills (ambiguity UI) ── */}
      {activeTypes.length > 0 && (
        <div className="mt-2 px-1 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-slate-600 uppercase tracking-wider">Detecting:</span>
          {activeTypes.map((type) => {
            const meta = TYPE_META[type];
            return (
              <button
                key={type}
                type="button"
                onClick={() => toggleType(type)}
                title={`${meta.label} — click to exclude from this investigation`}
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-mono font-medium transition-all",
                  meta.bg, meta.text, meta.border,
                  "hover:opacity-80"
                )}
              >
                {meta.label}
                <X className="w-2.5 h-2.5 opacity-60" />
              </button>
            );
          })}
          <span className="text-[10px] text-slate-700 ml-1">
            {activeTypes.length === 1 ? "1 type active" : `${activeTypes.length} types active`}
            {!showAmbiguity && " — click ? to change"}
          </span>
        </div>
      )}
    </form>
  );
}