"use client";

import { useMemo } from "react";
import * as Accordion from "@radix-ui/react-accordion";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Loader2,
  Search,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useInvestigationStore,
  type ModuleResultEntry,
  type PlaybookResults,
  type ResultStatus,
} from "@/store/useInvestigationStore";

/* ── Envelope shape (mirrors backend/normalize.py) ─────────────── */

type EnvelopeStat = { label: string; value: string | number };
type EnvelopeTable = {
  name: string;
  columns: string[];
  rows: Array<Array<string | number | null>>;
};
type EnvelopeError = { code?: string; message?: string; hint?: string };
type Envelope = {
  ok?: boolean;
  module?: string;
  summary?: { title?: string; stats?: EnvelopeStat[]; badges?: string[] };
  artifacts?: Record<string, string[]>;
  tables?: EnvelopeTable[];
  raw?: Record<string, unknown>;
  errors?: EnvelopeError[];
};

/* ── Status icon ───────────────────────────────────────────────── */

function StatusBadge({ status }: { status: ResultStatus }) {
  if (status === "done") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-400">
        <CheckCircle2 className="w-3.5 h-3.5" />
        Complete
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-rose-400">
        <AlertCircle className="w-3.5 h-3.5" />
        Failed
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-cyan-300">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Running
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
      <Clock3 className="w-3.5 h-3.5" />
      Queued
    </span>
  );
}

/* ── Per-module card ───────────────────────────────────────────── */

function moduleLabel(module: string, entry: ModuleResultEntry): string {
  if (entry.label) return entry.label;
  return module
    .replace(/^tasks\./, "")
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ModuleCard({ module, entry }: { module: string; entry: ModuleResultEntry }) {
  const env = (entry.result ?? {}) as Envelope;
  const stats = env.summary?.stats ?? [];
  const tables = env.tables ?? [];
  const artifactGroups = useMemo(
    () =>
      Object.entries(env.artifacts ?? {}).filter(
        ([, values]) => Array.isArray(values) && values.length > 0,
      ),
    [env.artifacts],
  );
  const errors = env.errors ?? [];
  const hasResult = entry.result !== null;
  const title = env.summary?.title ?? moduleLabel(module, entry);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-md overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-5 py-3 border-b border-white/[0.05] flex items-center justify-between gap-3 bg-white/[0.02]">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-100 truncate">{title}</h3>
          <p className="text-[11px] text-slate-500 mt-0.5 font-mono truncate">
            {moduleLabel(module, entry)}
          </p>
        </div>
        <StatusBadge status={entry.status} />
      </div>

      {/* Body */}
      <div className="p-5 space-y-4">
        {!hasResult && entry.status !== "error" ? (
          <div className="text-[12px] text-slate-500 italic">
            Waiting for module to return data…
          </div>
        ) : null}

        {/* Errors */}
        {errors.length > 0 ? (
          <div className="rounded-lg border border-rose-900/60 bg-rose-950/30 px-3 py-2 space-y-1">
            {errors.map((err, idx) => (
              <div
                key={`${err.code ?? "err"}-${idx}`}
                className="text-[12px] text-rose-300 flex gap-2"
              >
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <div>
                  <div>{err.message ?? "Module failed"}</div>
                  {err.hint ? (
                    <div className="text-rose-400/70 text-[11px] mt-0.5">{err.hint}</div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {/* Summary stats */}
        {stats.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {stats.map((s) => (
              <div
                key={s.label}
                className="rounded-lg border border-white/[0.06] bg-black/30 px-3 py-2"
              >
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-mono">
                  {s.label}
                </div>
                <div className="text-sm text-slate-100 font-mono mt-0.5 truncate">
                  {String(s.value)}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {/* Tables (the most useful view for beginners) */}
        {tables.length > 0 ? (
          <div className="space-y-3">
            {tables.slice(0, 2).map((table) => (
              <div
                key={table.name}
                className="rounded-lg border border-white/[0.06] bg-black/30 overflow-hidden"
              >
                <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06] text-[11px] font-mono text-slate-300">
                  {table.name}
                </div>
                <div className="overflow-auto max-h-72">
                  <table className="w-full text-[11px] font-mono">
                    <thead className="bg-black/40 text-slate-500 sticky top-0">
                      <tr>
                        {table.columns.map((c) => (
                          <th
                            key={c}
                            className="text-left px-3 py-1.5 border-b border-white/[0.05] font-normal whitespace-nowrap"
                          >
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.rows.slice(0, 25).map((row, i) => (
                        <tr
                          key={`${table.name}-${i}`}
                          className="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02]"
                        >
                          {row.map((cell, j) => (
                            <td
                              key={`${i}-${j}`}
                              className="px-3 py-1.5 text-slate-300 align-top"
                            >
                              {cell === null ? "—" : String(cell)}
                            </td>
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

        {/* Advanced disclosure: artifacts + raw JSON behind Radix Accordion */}
        {(artifactGroups.length > 0 || env.raw) ? (
          <Accordion.Root type="multiple" className="space-y-1.5">
            {artifactGroups.length > 0 ? (
              <Accordion.Item
                value="artifacts"
                className="rounded-lg border border-white/[0.06] bg-black/20 overflow-hidden"
              >
                <Accordion.Header>
                  <Accordion.Trigger className="group w-full flex items-center justify-between px-3 py-2 text-[11px] font-mono uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors">
                    <span>Collected Artifacts ({artifactGroups.reduce((s, [, v]) => s + v.length, 0)})</span>
                    <ChevronDown className="w-3.5 h-3.5 transition-transform group-data-[state=open]:rotate-180" />
                  </Accordion.Trigger>
                </Accordion.Header>
                <Accordion.Content className="data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up overflow-hidden">
                  <div className="px-3 pb-3 space-y-2">
                    {artifactGroups.map(([name, values]) => (
                      <div key={name}>
                        <div className="text-[10px] text-slate-600 uppercase font-mono tracking-widest mb-1">
                          {name}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {values.slice(0, 40).map((v) => (
                            <span
                              key={v}
                              className="text-[11px] font-mono rounded-md border border-white/[0.06] bg-white/[0.03] px-2 py-0.5 text-slate-300"
                            >
                              {v}
                            </span>
                          ))}
                          {values.length > 40 ? (
                            <span className="text-[10px] text-slate-600">
                              +{values.length - 40} more
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </Accordion.Content>
              </Accordion.Item>
            ) : null}

            {env.raw ? (
              <Accordion.Item
                value="raw"
                className="rounded-lg border border-white/[0.06] bg-black/20 overflow-hidden"
              >
                <Accordion.Header>
                  <Accordion.Trigger className="group w-full flex items-center justify-between px-3 py-2 text-[11px] font-mono uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors">
                    <span>View Raw Data (JSON)</span>
                    <ChevronDown className="w-3.5 h-3.5 transition-transform group-data-[state=open]:rotate-180" />
                  </Accordion.Trigger>
                </Accordion.Header>
                <Accordion.Content className="data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up overflow-hidden">
                  <pre className="text-[11px] text-slate-400 font-mono bg-black/40 px-3 py-3 overflow-auto max-h-80 whitespace-pre-wrap break-all">
                    {JSON.stringify(env.raw ?? env, null, 2)}
                  </pre>
                </Accordion.Content>
              </Accordion.Item>
            ) : null}
          </Accordion.Root>
        ) : null}
      </div>
    </div>
  );
}

/* ── Per-playbook section ──────────────────────────────────────── */

function PlaybookGroup({ pb, id }: { pb: PlaybookResults; id: string }) {
  const modules = useMemo(() => Object.entries(pb.modules), [pb.modules]);
  const doneCount = modules.filter(
    ([, m]) => m.status === "done" || m.status === "error",
  ).length;
  const total = modules.length;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-indigo-400 font-medium">
            Investigation
          </div>
          <h2 className="text-base text-slate-100 mt-0.5 font-mono">{pb.target}</h2>
        </div>
        <div className="text-[11px] text-slate-400 font-mono whitespace-nowrap">
          {doneCount} / {total} modules
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {modules.map(([module, entry]) => (
          <ModuleCard key={`${id}-${module}`} module={module} entry={entry} />
        ))}
      </div>
    </section>
  );
}

/* ── Public component ──────────────────────────────────────────── */

export function InlineResults() {
  const resultStore = useInvestigationStore((s) => s.resultStore);
  const playbooks = Object.entries(resultStore).sort(
    ([, a], [, b]) => b.startedAt - a.startedAt,
  );

  if (playbooks.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.02] px-6 py-10 text-center">
        <div className="mx-auto w-10 h-10 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-3">
          <Search className="w-4 h-4 text-indigo-300" />
        </div>
        <p className="text-sm text-slate-300">Enter a target above to start investigating.</p>
        <p className="text-[12px] text-slate-500 mt-1 inline-flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" />
          Try an IP, domain, email, or username.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-8")}>
      {playbooks.map(([id, pb]) => (
        <PlaybookGroup key={id} id={id} pb={pb} />
      ))}
    </div>
  );
}
