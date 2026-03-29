"use client";

import { useState } from "react";
import {
  FileText,
  Download,
  FileJson,
  FileCode,
  ClipboardCheck,
  Clock,
  Shield,
  Database,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useInvestigationStore } from "@/store/useInvestigationStore";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  format: "PDF" | "JSON" | "STIX" | "CSV";
  icon: React.ElementType;
}

const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: "executive-summary",
    name: "Executive Summary",
    description: "High-level overview with key findings and risk assessment",
    format: "PDF",
    icon: FileText,
  },
  {
    id: "technical-report",
    name: "Technical Report",
    description: "Detailed technical findings with IOCs and evidence",
    format: "PDF",
    icon: ClipboardCheck,
  },
  {
    id: "stix-bundle",
    name: "STIX 2.1 Bundle",
    description: "Structured Threat Intelligence in STIX format",
    format: "JSON",
    icon: FileJson,
  },
  {
    id: "raw-data",
    name: "Raw Data Export",
    description: "Complete dataset in machine-readable format",
    format: "JSON",
    icon: FileCode,
  },
  {
    id: "ioc-list",
    name: "IOC List",
    description: "Indicators of Compromise for security tools",
    format: "CSV",
    icon: Database,
  },
];

export default function ReportsPage() {
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const graphData = useInvestigationStore((s) => s.graphData);
  const streamLog = useInvestigationStore((s) => s.streamLog);

  const handleGenerate = async (templateId: string) => {
    setGeneratingId(templateId);
    // Simulate report generation
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setGeneratingId(null);
  };

  const handleDownload = (templateId: string) => {
    // Simulate download
    console.log("Downloading report:", templateId);
  };

  const nodeCount = graphData?.nodes.length ?? 0;
  const edgeCount = graphData?.edges.length ?? 0;

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Reports</h1>
          <p className="text-sm text-slate-400 mt-1">Generate and export investigation reports</p>
        </div>

        {/* Current Investigation Summary */}
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Current Investigation</h2>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-800/30">
              <div className="text-2xl font-bold text-cyan-400">{nodeCount}</div>
              <div className="text-xs text-slate-500 mt-1">Entities</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/30">
              <div className="text-2xl font-bold text-violet-400">{edgeCount}</div>
              <div className="text-xs text-slate-500 mt-1">Relationships</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/30">
              <div className="text-2xl font-bold text-amber-400">{streamLog.length}</div>
              <div className="text-xs text-slate-500 mt-1">Log Entries</div>
            </div>
          </div>
        </div>

        {/* Report Templates */}
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Available Reports</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {REPORT_TEMPLATES.map((template) => {
              const Icon = template.icon;
              const isGenerating = generatingId === template.id;

              return (
                <div
                  key={template.id}
                  className="glass-panel rounded-2xl p-5 flex flex-col gap-4 hover:border-cyan-500/30 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-cyan-400" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-slate-100">{template.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {template.format}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">{template.description}</p>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => handleGenerate(template.id)}
                      disabled={isGenerating}
                      className={cn(
                        "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors",
                        isGenerating
                          ? "bg-slate-800 text-slate-500 cursor-wait"
                          : "bg-cyan-600 hover:bg-cyan-500 text-white"
                      )}
                    >
                      {isGenerating ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <ClipboardCheck className="w-3.5 h-3.5" />
                          Generate
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleDownload(template.id)}
                      className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center gap-2"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Export Options */}
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Scheduled Reports</h2>
          </div>
          <div className="text-sm text-slate-400">
            Configure automated report generation on a schedule. Reports will be generated based on
            the current graph state and delivered via email or stored in the workspace.
          </div>
          <button className="mt-4 px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors">
            Configure Schedule
          </button>
        </div>
      </div>
    </div>
  );
}
