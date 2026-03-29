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
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Reports</h1>
          <p className="text-sm text-slate-400 mt-1">
            Generate and export investigation reports from accumulated STIX 2.1 data
          </p>
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
          {nodeCount === 0 && (
            <p className="text-xs text-slate-500 mt-3">
              Run OSINT modules from the Dashboard or Tools page to accumulate data, then return here to generate reports.
            </p>
          )}
        </div>

        {/* Report Templates */}
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Available Reports</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {REPORT_TEMPLATES.map((template) => (
              <ReportCard
                key={template.id}
                template={template}
                onDownload={handleDownload}
              />
            ))}
          </div>
        </div>

        {/* Scheduled Reports placeholder */}
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Scheduled Reports</h2>
          </div>
          <div className="text-sm text-slate-400">
            Automated report generation and delivery is available in the Enterprise edition.
            Connect your SMTP server and define schedules via environment variables.
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
    <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 hover:border-cyan-500/30 transition-colors">
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

      {/* Status feedback */}
      {state === "error" && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-950/30 rounded-lg px-3 py-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          {error}
        </div>
      )}
      {state === "success" && (
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/30 rounded-lg px-3 py-2">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          Report ready — click Download to save
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button
          onClick={generate}
          disabled={state === "generating"}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors",
            state === "generating"
              ? "bg-slate-800 text-slate-500 cursor-wait"
              : "bg-cyan-600 hover:bg-cyan-500 text-white"
          )}
        >
          {state === "generating" ? (
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
          onClick={() => content && onDownload(content, template.id, template.downloadMime)}
          disabled={state !== "success"}
          className={cn(
            "px-4 py-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-2",
            state === "success"
              ? "bg-slate-800 hover:bg-slate-700 text-slate-300"
              : "bg-slate-800/50 text-slate-600 cursor-not-allowed"
          )}
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </button>
      </div>
    </div>
  );
}
