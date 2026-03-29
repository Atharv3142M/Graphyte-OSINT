"use client";

import { ModuleCards } from "@/components/ModuleCards";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export default function ToolsPage() {
  const appendLog = useInvestigationStore((s) => s.appendLog);

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-4 max-w-7xl mx-auto space-y-3">
        {/* Header */}
        <div>
          <h1 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">OSINT Modules</h1>
          <p className="text-[10px] text-slate-600 mt-0.5">Individual reconnaissance and analysis tools</p>
        </div>

        {/* Module Grid */}
        <ModuleCards onStreamLog={(line) => appendLog(line)} />
      </div>
    </div>
  );
}
