"use client";

import { useState, useCallback } from "react";
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
  AlertCircle,
  CheckCircle2,
  Key,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useInvestigationStore } from "@/store/useInvestigationStore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  format: "PDF" | "JSON" | "STIX" | "CSV";
  icon: React.ElementType;
  downloadMime?: string;
  downloadExt: string;
}

const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: "executive-summary",
    name: "Executive Summary",
    description: "High-level overview with key findings and risk assessment for stakeholders",
    format: "PDF",
    icon: FileText,
    downloadExt: "md",
  },
  {
    id: "technical-report",
    name: "Technical Report",
    description: "Detailed technical findings with IOCs, evidence chain, and module results",
    format: "PDF",
    icon: ClipboardCheck,
    downloadExt: "md",
  },
  {
    id: "stix-bundle",
    name: "STIX 2.1 Bundle",
    description: "Structured Threat Intelligence in OASIS STIX 2.1 format for sharing",
    format: "JSON",
    icon: FileJson,
    downloadMime: "application/json",
    downloadExt: "json",
  },
  {
    id: "raw-data",
    name: "Raw Data Export",
    description: "Complete investigation dataset in machine-readable JSON format",
    format: "JSON",
    icon: FileCode,
    downloadMime: "application/json",
    downloadExt: "json",
  },
  {
    id: "ioc-list",
    name: "IOC List",
    description: "Indicators of Compromise — IP addresses, domains, URLs, emails in CSV",
    format: "CSV",
    icon: Database,
    downloadMime: "text/csv",
    downloadExt: "csv",
  },
];

type GenerationState = "idle" | "generating" | "success" | "error";

function useReportGeneration(reportId: string) {
  const [state, setState] = useState<GenerationState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);

  const generate = useCallback(async () => {
    setState("generating");
    setError(null);
    setContent(null);
    try {
      const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setContent(data.content);
      setState("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  }, [reportId]);

  return { state, error, content, generate };
}

export default function ReportsPage() {
  const graphData = useInvestigationStore((s) => s.graphData);
  const streamLog = useInvestigationStore((s) => s.streamLog);

  const nodeCount = graphData?.nodes.length ?? 0;
  const edgeCount = graphData?.edges.length ?? 0;

  const handleDownload = (
    content: string,
    reportId: string,
    format?: string
  ) => {
    if (!content) return;
    const tmpl = REPORT_TEMPLATES.find((t) => t.id === reportId);
    const mimeType = tmpl?.downloadMime || "text/plain";
    const ext = tmpl?.downloadExt || "txt";
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `osint-report-${reportId}-${Date.now()}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-7 max-w-6xl mx-auto space-y-5">
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6">
          <h1 className="text-2xl font-semibold text-slate-100">Reports & Exports</h1>
          <p className="text-sm text-slate-400 mt-2">
            Generate executive, technical, and machine-readable outputs from normalized investigation data.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-3 h-3 text-cyan-600" />
            <h2 className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">Current Investigation</h2>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg border border-slate-800 p-3 bg-slate-950/50">
              <div className="text-lg font-bold text-cyan-400 font-mono">{nodeCount}</div>
              <div className="text-[9px] text-slate-600 uppercase tracking-wider mt-0.5">Entities</div>
            </div>
            <div className="rounded-lg border border-slate-800 p-3 bg-slate-950/50">
              <div className="text-lg font-bold text-violet-400 font-mono">{edgeCount}</div>
              <div className="text-[9px] text-slate-600 uppercase tracking-wider mt-0.5">Relationships</div>
            </div>
            <div className="rounded-lg border border-slate-800 p-3 bg-slate-950/50">
              <div className="text-lg font-bold text-amber-400 font-mono">{streamLog.length}</div>
              <div className="text-[9px] text-slate-600 uppercase tracking-wider mt-0.5">Log Entries</div>
            </div>
          </div>
          {nodeCount === 0 && (
            <p className="text-[10px] text-slate-600 mt-2 font-mono">
              Run OSINT modules to accumulate data, then return here to generate reports.
            </p>
          )}
        </div>

        <div>
          <h2 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">Available Reports</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {REPORT_TEMPLATES.map((template) => (
              <ReportCard
                key={template.id}
                template={template}
                onDownload={handleDownload}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportCard({
  template,
  onDownload,
}: {
  template: ReportTemplate;
  onDownload: (content: string, reportId: string, mime?: string) => void;
}) {
  const { state, error, content, generate } = useReportGeneration(template.id);
  const Icon = template.icon;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 border border-cyan-900 bg-cyan-950/50 flex items-center justify-center">
            <Icon className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-slate-200 font-mono">{template.name}</h3>
            <div className="flex items-center gap-1 mt-0.5">
              <span className="text-[9px] px-1 py-0.5 border border-slate-800 text-slate-500 uppercase tracking-wider">
                {template.format}
              </span>
            </div>
          </div>
        </div>
      </div>

      <p className="text-[10px] text-slate-500 leading-relaxed font-mono">{template.description}</p>

      {/* Status feedback */}
      {state === "error" && (
        <div className="flex items-center gap-1.5 text-[10px] text-red-400 border border-red-900/50 bg-red-950/30 px-2 py-1.5">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {error}
        </div>
      )}
      {state === "success" && (
        <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 border border-emerald-900/50 bg-emerald-950/30 px-2 py-1.5">
          <CheckCircle2 className="w-3 h-3 shrink-0" />
          Report ready
        </div>
      )}

      <div className="flex gap-1.5 pt-1">
        <button
          onClick={generate}
          disabled={state === "generating"}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider transition-colors",
            state === "generating"
              ? "border border-slate-800 text-slate-600 cursor-wait"
              : "soc-btn-primary"
          )}
        >
          {state === "generating" ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Generating
            </>
          ) : (
            <>
              <ClipboardCheck className="w-3 h-3" />
              Generate
            </>
          )}
        </button>
        <button
          onClick={() => content && onDownload(content, template.id, template.downloadMime)}
          disabled={state !== "success"}
          className={cn(
            "px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider transition-colors flex items-center gap-1.5",
            state === "success"
              ? "border border-slate-700 text-slate-400 hover:bg-slate-900"
              : "border border-slate-800 text-slate-700 cursor-not-allowed"
          )}
        >
          <Download className="w-3 h-3" />
          Download
        </button>
      </div>
    </div>
  );
}
