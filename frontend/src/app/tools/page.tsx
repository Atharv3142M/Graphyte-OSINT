"use client";

import { FlaskConical, Radio, Sparkles } from "lucide-react";
import { ModuleCards } from "@/components/ModuleCards";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export default function ToolsPage() {
  const appendLog = useInvestigationStore((s) => s.appendLog);

  return (
    <div className="h-full overflow-y-auto bg-transparent">
      <div className="p-7 max-w-7xl mx-auto space-y-5">
        <div className="soc-panel rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-2xl">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Tools</div>
              <h1 className="text-2xl font-semibold text-slate-100 mt-1">Ad-hoc Module Runner</h1>
              <p className="text-sm text-slate-400 mt-2">
                Execute a single module with custom input. Output streams to console and normalized results panel.
              </p>
            </div>
            <div className="hidden md:flex items-center gap-2 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-800 bg-slate-900/80">
                <FlaskConical className="w-3.5 h-3.5 text-cyan-400" /> Module Lab
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-800 bg-slate-900/80">
                <Radio className="w-3.5 h-3.5 text-violet-400" /> Live Stream
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-400">
          <div className="inline-flex items-center gap-1.5 text-cyan-300 mb-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Tip
          </div>
          Use `example.com`, `8.8.8.8`, or known usernames as baseline probes before running deep scans.
        </div>

        <ModuleCards onStreamLog={(line) => appendLog(line)} />
      </div>
    </div>
  );
}
