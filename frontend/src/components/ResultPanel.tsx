"use client";

import { useState } from "react";
import {
  X,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Loader,
  Clock,
  ExternalLink,
  Globe,
  Shield,
  Wifi,
  Database,
  Code2,
  Eye,
  Scan,
  FileText,
  UserCheck,
  Hash,
  Mail,
  Phone,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useInvestigationStore,
  type ModuleResultEntry,
  type ResultStatus,
  type PlaybookResults,
} from "@/store/useInvestigationStore";

/* ── Status ring ─────────────────────────────────────────── */

function StatusRing({ status }: { status: ResultStatus }) {
  switch (status) {
    case "pending":
      return <Clock className="w-3.5 h-3.5 text-slate-500" />;
    case "running":
      return <Loader className="w-3.5 h-3.5 text-cyan-400 animate-spin" />;
    case "done":
      return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
    case "error":
      return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
  }
}

/* ── Grade badge helper ──────────────────────────────────── */

function GradeBadge({ grade }: { grade: string }) {
  const cls =
    grade.startsWith("A") ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
    : grade === "B" ? "text-cyan-400 border-cyan-500/30 bg-cyan-500/10"
    : grade === "C" ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
    : "text-red-400 border-red-500/30 bg-red-500/10";
  return (
    <span className={cn("text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border", cls)}>
      {grade}
    </span>
  );
}

/* ── Port Scan renderer ─────────────────────────────────── */

function PortScanTable({ data }: { data: Record<string, unknown> }) {
  const ports = data.open_ports as Array<{ port: number; protocol?: string; service?: string }> | undefined
    ?? data.ports as Array<{ port: number; protocol?: string; service?: string }> | undefined
    ?? [];
  if (!ports.length) {
    return <div className="text-xs text-slate-600 font-mono">No open ports found</div>;
  }
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
        {ports.length} open port{ports.length !== 1 ? "s" : ""} found
      </div>
      <div className="space-y-0.5 max-h-48 overflow-y-auto">
        {ports.slice(0, 30).map((p, i) => (
          <div key={i} className="flex items-center gap-2 px-2 py-1 bg-slate-900 rounded border border-slate-800">
            <span className="text-xs font-mono text-cyan-400 w-12 text-right">{p.port}</span>
            <span className="text-[10px] text-slate-500 uppercase">{p.protocol ?? "tcp"}</span>
            <span className="text-xs font-mono text-slate-300">{p.service ?? "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── HTTP Security renderer ──────────────────────────────── */

function HttpSecurityGrid({ data }: { data: Record<string, unknown> }) {
  const present = data.present_headers as string[] ?? [];
  const missing = data.missing_headers as string[] ?? [];
  const grade = (data.grade as string) ?? "—";
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <GradeBadge grade={grade} />
        <span className="text-[10px] text-slate-500">Security Grade</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <div className="text-[10px] text-emerald-500 uppercase tracking-wider mb-1">
            ✓ Present ({present.length})
          </div>
          <div className="space-y-0.5">
            {present.slice(0, 8).map((h) => (
              <div key={h} className="text-[10px] font-mono text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded">
                {h}
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-red-500 uppercase tracking-wider mb-1">
            ✗ Missing ({missing.length})
          </div>
          <div className="space-y-0.5">
            {missing.slice(0, 8).map((h) => (
              <div key={h} className="text-[10px] font-mono text-red-400 bg-red-500/5 px-2 py-0.5 rounded">
                {h}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Tech Stack renderer ─────────────────────────────────── */

function TechStackGrid({ data }: { data: Record<string, unknown> }) {
  const techs = data.tech_stack as Array<{ name: string; category?: string; confidence?: number }> | undefined
    ?? data.technologies as Array<{ name: string; category?: string; confidence?: number }> | undefined
    ?? [];
  const cats = data.categories as Record<string, string[]> | undefined ?? {};
  if (!techs.length && !Object.keys(cats).length) {
    return <div className="text-xs text-slate-600 font-mono">{JSON.stringify(data, null, 2)}</div>;
  }
  const CATEGORY_COLORS: Record<string, string> = {
    "Server": "text-cyan-400",
    "CMS": "text-violet-400",
    "Framework": "text-amber-400",
    "Analytics": "text-pink-400",
    "JavaScript": "text-yellow-400",
    "Database": "text-emerald-400",
  };
  return (
    <div className="space-y-2">
      {Object.entries(cats).map(([cat, items]) => (
        <div key={cat}>
          <div className={cn("text-[10px] uppercase tracking-wider mb-1", CATEGORY_COLORS[cat] ?? "text-slate-400")}>
            {cat}
          </div>
          <div className="flex flex-wrap gap-1">
            {(Array.isArray(items) ? items : []).slice(0, 15).map((t) => (
              <span key={t} className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
                {t}
              </span>
            ))}
          </div>
        </div>
      ))}
      {techs.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {techs.slice(0, 20).map((t, i) => (
            <span key={i} className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
              {t.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── CyberNinja / xRecon renderer ───────────────────────── */

function ReconGrid({ data, icon: Icon }: { data: Record<string, unknown>; icon: React.ElementType }) {
  const results = (data.results as Record<string, unknown>[]) ?? (data.data as Record<string, unknown>[]) ?? [];
  if (!results.length) {
    const flat = Object.entries(data).filter(([k]) => !["results", "data", "error"].includes(k));
    if (flat.length === 0) return <div className="text-xs text-slate-600 font-mono">No results</div>;
    return (
      <div className="space-y-0.5">
        {flat.slice(0, 10).map(([k, v]) => (
          <div key={k} className="flex items-start gap-2 text-[10px]">
            <span className="text-slate-500 uppercase tracking-wider w-20 flex-shrink-0">{k}</span>
            <span className="text-slate-300 font-mono">{JSON.stringify(v)}</span>
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-1">
      {results.slice(0, 30).map((r, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1 bg-slate-900 rounded border border-slate-800">
          <Icon className="w-3 h-3 text-cyan-400 flex-shrink-0" />
          <span className="text-xs font-mono text-slate-300 flex-1 truncate">
            {(r.source as string) ?? (r.platform as string) ?? (r.type as string) ?? `result ${i}`}
          </span>
          {r.url ? (
            <a href={String(r.url)} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-cyan-400">
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/* ── Deep Scraper renderer ───────────────────────────────── */

function DeepScraperTabs({ data }: { data: Record<string, unknown> }) {
  const emails = (data.emails as string[]) ?? (data.email_addresses as string[]) ?? [];
  const phones = (data.phones as string[]) ?? (data.phone_numbers as string[]) ?? [];
  const links = (data.links as string[]) ?? (data.external_links as string[]) ?? [];
  const profiles = (data.social_profiles as Record<string, string>[]) ?? (data.profiles as Record<string, string>[]) ?? [];
  const [tab, setTab] = useState<"emails" | "phones" | "links" | "profiles">("emails");
  const tabs = [
    { key: "emails", label: "Emails", count: emails.length, icon: Mail },
    { key: "phones", label: "Phones", count: phones.length, icon: Phone },
    { key: "links", label: "Links", count: links.length, icon: Globe },
    { key: "profiles", label: "Profiles", count: profiles.length, icon: UserCheck },
  ].filter((t) => t.count > 0);
  if (tabs.length === 0) {
    return <div className="text-xs text-slate-600 font-mono">{JSON.stringify(data, null, 2)}</div>;
  }
  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as typeof tab)}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border transition-colors",
              tab === t.key ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-400" : "border-slate-700 text-slate-500 hover:border-slate-600"
            )}
          >
            <t.icon className="w-3 h-3" />
            {t.label}
            <span className="text-[9px] text-slate-600">{t.count}</span>
          </button>
        ))}
      </div>
      <div className="max-h-48 overflow-y-auto space-y-0.5">
        {tab === "emails" && emails.slice(0, 20).map((e, i) => (
          <div key={i} className="text-xs font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 truncate">{e}</div>
        ))}
        {tab === "phones" && phones.slice(0, 20).map((p, i) => (
          <div key={i} className="text-xs font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800">{p}</div>
        ))}
        {tab === "links" && links.slice(0, 20).map((l, i) => (
          <a key={i} href={l} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] font-mono text-cyan-400 bg-slate-900 px-2 py-1 rounded border border-slate-800 hover:border-cyan-700 truncate">
            <ExternalLink className="w-3 h-3 flex-shrink-0" />{l}
          </a>
        ))}
        {tab === "profiles" && profiles.slice(0, 20).map((p, i) => (
          <div key={i} className="flex items-center gap-2 px-2 py-1 bg-slate-900 rounded border border-slate-800">
            <span className="text-xs font-mono text-slate-300">{(p.platform as string) ?? Object.keys(p)[0]}</span>
            {Object.values(p)[0] && (
              <a href={Object.values(p)[0] as string} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-cyan-400 ml-auto">
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Social Hunter renderer ─────────────────────────────── */

function SocialGrid({ data }: { data: Record<string, unknown> }) {
  const found = data.found as Array<{ platform: string; url: string; status?: string }> | undefined;
  const all = data.platforms as Record<string, string> | undefined;
  if (!found && !all) return null;
  return (
    <div className="space-y-1">
      {(found ?? []).slice(0, 30).map((item, i) => (
        <a
          key={i}
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-2 py-1.5 bg-slate-900 rounded border border-slate-800 hover:border-emerald-700 transition-colors group"
        >
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-xs font-mono text-slate-300">{item.platform}</span>
          </div>
          <ExternalLink className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-colors" />
        </a>
      ))}
      {(found ?? []).length === 0 && (
        <div className="text-xs text-slate-600 text-center py-4 font-mono">No platforms found</div>
      )}
    </div>
  );
}

/* ── DNS table renderer ─────────────────────────────────── */

function DNSTable({ data }: { data: Record<string, unknown> }) {
  const records = data.records as Record<string, string[]> | undefined;
  if (!records) {
    return <div className="text-xs text-slate-500 font-mono">{JSON.stringify(data, null, 2)}</div>;
  }
  return (
    <div className="space-y-2">
      {Object.entries(records).map(([type, values]) => (
        <div key={type}>
          <div className="text-[10px] font-mono text-slate-400 mb-1 uppercase tracking-wider">{type} Records</div>
          <div className="space-y-0.5">
            {(values ?? []).slice(0, 10).map((val, i) => (
              <div key={i} className="text-xs font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 truncate">
                {val}
              </div>
            ))}
            {(values ?? []).length > 10 && (
              <div className="text-[10px] text-slate-600 pl-2">+{values.length - 10} more</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── SSL renderer ────────────────────────────────────────── */

function SSLCard({ data }: { data: Record<string, unknown> }) {
  const grade = (data.grade as string) ?? (data.tls_grade as string) ?? "—";
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <GradeBadge grade={grade} />
        <div className="text-xs text-slate-500">TLS Grade</div>
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-[10px]">
        {[
          ["Cipher", data.cipher as string],
          ["Version", data.tls_version as string],
          ["Expiry", data.expires_at as string],
          ["SANs", data.san_count as string ?? String((data.san_domains as string[])?.length ?? 0)],
        ].map(([label, val]) => val ? (
          <div key={label} className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
            <span className="text-slate-500 uppercase tracking-wider">{label}</span>
            <div className="text-slate-300 font-mono truncate">{String(val)}</div>
          </div>
        ) : null)}
      </div>
    </div>
  );
}

/* ── WHOIS renderer ─────────────────────────────────────── */

function WhoisCard({ data }: { data: Record<string, unknown> }) {
  const fields = [
    ["Registrar", data.registrar as string ?? data.registrar_name as string],
    ["Created", data.created_date as string ?? data.creation_date as string],
    ["Expires", data.expiry_date as string ?? data.expiration_date as string],
    ["Age", data.registrar_age as string ?? data.domain_age as string],
    ["Name Servers", Array.isArray(data.name_servers) ? (data.name_servers as string[]).join(", ") : (data.nameservers as string[])?.join(", ")],
  ];
  return (
    <div className="space-y-1">
      {fields.map(([label, val]) => val ? (
        <div key={label} className="flex items-start gap-2 text-xs">
          <span className="text-slate-500 uppercase tracking-wider w-20 flex-shrink-0 pt-0.5">{label}</span>
          <span className="text-slate-300 font-mono">{String(val)}</span>
        </div>
      ) : null)}
    </div>
  );
}

/* ── Cert Transparency renderer ─────────────────────────── */

function CertTransparencyCard({ data }: { data: Record<string, unknown> }) {
  const domains = data.subdomains as string[] ?? data.domains as string[] ?? [];
  const wildcard = data.wildcard_count as number ?? 0;
  return (
    <div className="space-y-2">
      {domains.length > 0 ? (
        <>
          <div className="text-xs text-slate-500 mb-1">{domains.length} subdomains found{wildcard > 0 ? ` + ${wildcard} wildcards` : ""}</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {domains.slice(0, 50).map((d, i) => (
              <div key={i} className="text-xs font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 truncate">
                {d}
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-xs text-slate-600 font-mono">No subdomains found</div>
      )}
    </div>
  );
}

/* ── Generic fallback ───────────────────────────────────── */

function GenericResult({ data }: { data: Record<string, unknown> }) {
  return (
    <pre className="text-xs text-slate-400 font-mono bg-slate-900 rounded border border-slate-800 p-2 overflow-auto max-h-60 whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

/* ── Master renderer ────────────────────────────────────── */

function ResultRenderer({ module, result }: { module: string; result: Record<string, unknown> | null }) {
  if (!result) return <div className="text-xs text-slate-600 font-mono">Waiting for data…</div>;
  const m = module.toLowerCase().replace(/ /g, "_");
  switch (m) {
    case "dns_intel": case "dns": return <DNSTable data={result} />;
    case "ssl_analyzer": case "ssl": return <SSLCard data={result} />;
    case "social_hunter": case "social-hunter": return <SocialGrid data={result} />;
    case "whois": case "whois_lookup": return <WhoisCard data={result} />;
    case "cert_transparency": case "cert-transparency": return <CertTransparencyCard data={result} />;
    case "port_scan": case "port_scan_results": return <PortScanTable data={result} />;
    case "http_security": case "http-security": return <HttpSecurityGrid data={result} />;
    case "tech_stack": case "tech-stack": return <TechStackGrid data={result} />;
    case "cyberninja_passive": return <ReconGrid data={result} icon={Eye} />;
    case "xrecon": case "x_recon": return <ReconGrid data={result} icon={Scan} />;
    case "deep_scraper": case "deep-scraper": return <DeepScraperTabs data={result} />;
    case "shodan_recon": case "shodan": return <ReconGrid data={result} icon={Shield} />;
    case "censys_recon": case "censys": return <ReconGrid data={result} icon={Database} />;
    case "graysentinel_ingest": return <ReconGrid data={result} icon={FileText} />;
    default: return <GenericResult data={result} />;
  }
}

/* ── Module section row ─────────────────────────────────── */

function ModuleSection({ module, entry }: { module: string; entry: ModuleResultEntry }) {
  const [open, setOpen] = useState<boolean>(false);
  const isDone = entry.status === "done" || entry.status === "error";

  return (
    <div className="border-b border-slate-800 last:border-b-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-slate-900/50 transition-colors text-left"
      >
        <StatusRing status={entry.status} />
        <span className="text-xs font-mono text-slate-300 flex-1">
          {module.replace(/_/g, " ").replace(/-/g, " ")}
        </span>
        {entry.result && Object.keys(entry.result).length > 0 && (
          <span className="text-[10px] text-slate-600 font-mono">1 result</span>
        )}
        {isDone ? (
          <ChevronDown className={cn("w-3 h-3 text-slate-600 transition-transform", open && "rotate-180")} />
        ) : (
          <ChevronRight className="w-3 h-3 text-slate-600" />
        )}
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1">
          {entry.status === "error" && entry.error && (
            <div className="text-xs text-red-400 font-mono mb-2 bg-red-950/30 border border-red-900/50 rounded px-2 py-1.5">
              {entry.error}
            </div>
          )}
          <ResultRenderer module={module} result={entry.result} />
        </div>
      )}
    </div>
  );
}

/* ── Playbook section (grouped by playbook) ──────────────── */

function PlaybookSection({ playbookId, pb }: { playbookId: string; pb: PlaybookResults }) {
  const [open, setOpen] = useState(true);
  const modules = Object.entries(pb.modules);
  const runningCount = modules.filter(([, m]) => m.status === "pending" || m.status === "running").length;
  const doneCount = modules.filter(([, m]) => m.status === "done").length;

  return (
    <div className="border-b border-slate-700/50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-900/40 hover:bg-slate-900/60 transition-colors text-left"
      >
        <Target className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
        <span className="text-xs font-mono text-slate-200 flex-1 truncate">{pb.target}</span>
        <div className="flex items-center gap-2">
          {runningCount > 0 && (
            <span className="text-[10px] text-cyan-400 font-mono">{runningCount} running</span>
          )}
          {doneCount > 0 && (
            <span className="text-[10px] text-emerald-400 font-mono">{doneCount} done</span>
          )}
        </div>
        {open ? (
          <ChevronDown className="w-3 h-3 text-slate-600" />
        ) : (
          <ChevronRight className="w-3 h-3 text-slate-600" />
        )}
      </button>
      {open && (
        <div>
          {modules.map(([module, entry]) => (
            <ModuleSection key={module} module={module} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main ResultPanel ────────────────────────────────────── */

interface ResultPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ResultPanel({ isOpen, onClose }: ResultPanelProps) {
  const resultStore = useInvestigationStore((s) => s.resultStore);
  const clearAllResults = useInvestigationStore((s) => s.clearAllResults);
  const playbooks = Object.entries(resultStore);
  const totalModules = playbooks.reduce(
    (sum, [, pb]) => sum + Object.keys(pb.modules).length, 0
  );

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20"
          onClick={onClose}
        />
      )}

      {/* Slide-over panel */}
      <div
        className={cn(
          "fixed right-0 top-0 bottom-0 z-40 w-[400px] flex flex-col transition-transform duration-200",
          "bg-slate-900 border-l border-slate-800",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="text-xs font-semibold text-slate-200 uppercase tracking-wider">Results</div>
            {totalModules > 0 && (
              <div className="text-[10px] text-slate-600 font-mono">{totalModules} modules</div>
            )}
          </div>
          <div className="flex items-center gap-1">
            {playbooks.length > 0 && (
              <button
                onClick={clearAllResults}
                className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors px-2 py-1"
                title="Clear all results"
              >
                Clear
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Results list */}
        <div className="flex-1 overflow-y-auto">
          {playbooks.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center mb-3">
                <Clock className="w-4 h-4 text-slate-600" />
              </div>
              <div className="text-xs text-slate-500 font-mono">No results yet</div>
              <div className="text-[10px] text-slate-700 mt-1 font-mono">Run an investigation to see live results here</div>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/50">
              {playbooks.map(([playbookId, pb]) => (
                <PlaybookSection key={playbookId} playbookId={playbookId} pb={pb} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
