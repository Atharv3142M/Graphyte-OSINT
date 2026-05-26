"use client";

import { useMemo, useState } from "react";
import * as Accordion from "@radix-ui/react-accordion";
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Clock3, Loader2, X, TerminalSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInvestigationStore, type ModuleResultEntry, type PlaybookResults, type ResultStatus } from "@/store/useInvestigationStore";

type Envelope = {
  ok?: boolean;
  module?: string;
  summary?: { title?: string; stats?: Array<{ label: string; value: string | number }>; badges?: string[] };
  artifacts?: Record<string, string[]>;
  tables?: Array<{ name: string; columns: string[]; rows: Array<Array<string | number | null>> }>;
  raw?: Record<string, unknown>;
  errors?: Array<{ code?: string; message?: string; hint?: string }>;
};

function StatusIcon({ status }: { status: ResultStatus }) {
  if (status === "done") return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
  if (status === "error") return <AlertCircle className="w-3.5 h-3.5 text-rose-500" />;
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 text-cyan-500 animate-spin" />;
  return <Clock3 className="w-3.5 h-3.5 text-slate-500" />;
}

function labelForModule(module: string, entry: ModuleResultEntry): string {
  if (entry.label) return entry.label;
  return module.replace(/^tasks\./, "").replace(/[_-]/g, " ");
}

function ModuleEnvelope({ entry }: { entry: ModuleResultEntry }) {
  const env = (entry.result ?? {}) as Envelope;
  const artifacts = env.artifacts ?? {};
  const artifactGroups = Object.entries(artifacts).filter(([, values]) => Array.isArray(values) && values.length > 0);
  const totalArtifacts = artifactGroups.reduce((s, [, v]) => s + v.length, 0);

  return (
    <div className="space-y-4">
      {/* ── Errors first — visible without scrolling ── */}
      {Array.isArray(env.errors) && env.errors.length > 0 ? (
        <div className="rounded-sm border border-rose-900 bg-rose-950/30 px-3 py-2">
          {env.errors.map((err, idx) => (
            <div key={`${err.code ?? "err"}-${idx}`} className="text-[11px] font-mono text-rose-400">
              <AlertCircle className="w-3 h-3 inline-block mr-1.5" />
              {err.message ?? "Module failed"}
              {err.hint ? <span className="text-rose-300/70 block mt-1 ml-4">• {err.hint}</span> : null}
            </div>
          ))}
        </div>
      ) : null}

      {/* ── Summary header (always visible) ── */}
      <div className="bg-[#08090A] border border-slate-800 rounded-sm p-3">
        <div className="text-[11px] text-slate-400 font-mono tracking-wide mb-2">
          <TerminalSquare className="w-3 h-3 inline-block mr-1.5" />
          {env.summary?.title ?? "Module output"}
        </div>
        {env.summary?.stats && env.summary.stats.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {env.summary.stats.map((s) => (
              <div key={s.label} className="border border-slate-800 bg-[#0C0C0E] rounded-sm px-2.5 py-2">
                <div className="text-[10px] text-slate-500 uppercase font-mono tracking-widest">{s.label}</div>
                <div className="text-xs text-slate-200 font-mono mt-1 truncate">{String(s.value)}</div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {/* ── Tables (always visible — the human-readable centerpiece) ── */}
      {Array.isArray(env.tables) && env.tables.length > 0 ? (
        <div className="space-y-3">
          <div className="text-[10px] uppercase font-mono tracking-widest text-slate-500">Tabular Data</div>
          {env.tables.slice(0, 3).map((table) => (
            <div key={table.name} className="rounded-sm border border-slate-800 bg-[#0C0C0E] overflow-hidden">
              <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 text-[11px] font-mono tracking-wide text-slate-300">{table.name}</div>
              <div className="overflow-auto max-h-64">
                <table className="w-full text-[11px] font-mono">
                  <thead className="bg-[#08090A] text-slate-500 sticky top-0">
                    <tr>
                      {table.columns.map((c) => (
                        <th key={c} className="text-left px-3 py-2 border-b border-slate-800 font-normal">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.slice(0, 50).map((row, i) => (
                      <tr key={`${table.name}-${i}`} className="border-b border-slate-800 hover:bg-slate-900/50 transition-colors last:border-0">
                        {row.map((cell, j) => (
                          <td key={`${i}-${j}`} className="px-3 py-1.5 text-slate-300">{cell === null ? "-" : String(cell)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* ── Artifacts + Raw JSON: hidden behind Radix accordion ── */}
      {(artifactGroups.length > 0 || env.raw) ? (
        <Accordion.Root type="multiple" className="space-y-1.5">
          {artifactGroups.length > 0 ? (
            <Accordion.Item value="artifacts" className="rounded-sm border border-slate-800 bg-[#08090A] overflow-hidden">
              <Accordion.Header>
                <Accordion.Trigger className="group w-full flex items-center justify-between px-3 py-2 text-[11px] font-mono uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors">
                  <span>Collected Artifacts ({totalArtifacts})</span>
                  <ChevronDown className="w-3.5 h-3.5 transition-transform group-data-[state=open]:rotate-180" />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className="overflow-hidden">
                <div className="px-3 pb-3 space-y-2">
                  {artifactGroups.map(([name, values]) => (
                    <div key={name} className="mt-1">
                      <div className="text-[10px] text-slate-600 font-mono uppercase tracking-widest mb-1.5">{name}</div>
                      <div className="flex flex-wrap gap-1.5">
                        {values.slice(0, 30).map((v) => (
                          <span key={v} className="text-[11px] font-mono rounded-sm border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">{v}</span>
                        ))}
                        {values.length > 30 ? (
                          <span className="text-[10px] text-slate-600 self-center">+{values.length - 30} more</span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </Accordion.Content>
            </Accordion.Item>
          ) : null}

          {env.raw ? (
            <Accordion.Item value="raw" className="rounded-sm border border-slate-800 bg-[#08090A] overflow-hidden">
              <Accordion.Header>
                <Accordion.Trigger className="group w-full flex items-center justify-between px-3 py-2 text-[11px] font-mono uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors">
                  <span>View Raw Data (JSON)</span>
                  <ChevronDown className="w-3.5 h-3.5 transition-transform group-data-[state=open]:rotate-180" />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className="overflow-hidden">
                <pre className="text-[11px] text-slate-400 font-mono bg-[#08090A] border-t border-slate-800 p-3 overflow-auto max-h-80 whitespace-pre-wrap break-all">
                  {JSON.stringify(env.raw ?? env, null, 2)}
                </pre>
              </Accordion.Content>
            </Accordion.Item>
          ) : null}
        </Accordion.Root>
      ) : null}
    </div>
  );
}

function ModuleSection({ module, entry }: { module: string; entry: ModuleResultEntry }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border-t border-slate-800 first:border-t-0">
      <button onClick={() => setOpen((v) => !v)} className="w-full px-4 py-3 flex items-center gap-3 hover:bg-[#0C0C0E] transition-colors">
        <StatusIcon status={entry.status} />
        <span className="text-[11px] font-mono uppercase tracking-widest text-slate-300 flex-1 text-left">{labelForModule(module, entry)}</span>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
      </button>
      {open ? <div className="px-4 pb-4"><ModuleEnvelope entry={entry} /></div> : null}
    </div>
  );
}

function PlaybookSection({ pb }: { pb: PlaybookResults }) {
  const modules = useMemo(() => Object.entries(pb.modules), [pb.modules]);
  const [open, setOpen] = useState(true);
  const doneCount = modules.filter(([, m]) => m.status === "done" || m.status === "error").length;

  return (
    <div className="border-b border-slate-800 last:border-b-0">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center gap-3 px-4 py-3 bg-[#08090A] hover:bg-slate-900 transition-colors border-b border-slate-800">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-200 flex-1 text-left truncate">Operation: {pb.target}</span>
        <span className="text-[10px] text-slate-500 font-mono tracking-widest">{doneCount}/{modules.length} MODULES</span>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
      </button>
      {open ? modules.map(([module, entry]) => <ModuleSection key={module} module={module} entry={entry} />) : null}
    </div>
  );
}

export function ResultPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const resultStore = useInvestigationStore((s) => s.resultStore);
  const clearAllResults = useInvestigationStore((s) => s.clearAllResults);
  const playbooks = Object.entries(resultStore);

  return (
    <>
      {isOpen ? <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm" onClick={onClose} /> : null}
      <div className={cn("fixed right-0 top-0 bottom-0 z-40 w-full md:w-[600px] border-l border-slate-800 bg-[#0C0C0E] transition-transform duration-300 ease-in-out shadow-[-10px_0_30px_rgba(0,0,0,0.5)]", isOpen ? "translate-x-0" : "translate-x-full")}>
        <div className="h-full flex flex-col">
          <div className="px-5 py-4 bg-[#08090A] border-b border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-mono tracking-widest text-slate-500 mb-1">Module Results</div>
              <div className="text-sm font-mono text-slate-200">Normalized Data Table</div>
            </div>
            <div className="flex items-center gap-3">
              {playbooks.length > 0 ? (
                <button onClick={clearAllResults} className="text-[11px] font-mono uppercase tracking-widest text-slate-500 border border-slate-700 bg-slate-900 hover:bg-slate-800 rounded-sm px-2 py-1 transition-colors">Clear Cache</button>
              ) : null}
              <button onClick={onClose} className="p-1.5 text-slate-500 hover:text-slate-200 hover:bg-slate-800 rounded-sm transition-colors border border-transparent"><X className="w-4 h-4" /></button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {playbooks.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-[11px] font-mono tracking-widest uppercase text-slate-600 border border-slate-800 px-4 py-2 rounded-sm border-dashed">No active playbooks</div>
              </div>
            ) : (
              playbooks.map(([id, pb]) => <PlaybookSection key={id} pb={pb} />)
            )}
          </div>
        </div>
      </div>
    </>
  );
}
