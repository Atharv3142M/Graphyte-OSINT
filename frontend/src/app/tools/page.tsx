"use client";

import { ModuleCards } from "@/components/ModuleCards";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export default function ToolsPage() {
  const appendLog = useInvestigationStore((s) => s.appendLog);

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-slate-100">OSINT Tools</h1>
          <p className="text-sm text-slate-400 mt-1">Individual reconnaissance and analysis modules</p>
        </div>

        {/* Module Grid */}
        <ModuleCards onStreamLog={(line) => appendLog(line)} />
      </div>
    </div>
  );
}
