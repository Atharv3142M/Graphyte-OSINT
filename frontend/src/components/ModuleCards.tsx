"use client";

import { useState, useCallback } from "react";
import {
  Globe,
  FileSearch,
  ShieldCheck,
  Lock,
  Cpu,
  FileCode2,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Network,
  ScanSearch,
  AtSign,
  MapPin,
  Route,
  Radar,
  Archive,
  MailSearch,
  UserCheck,
  FileText,
  Image,
  Shuffle,
  Github,
  Phone,
  Mail,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { runModule, WS_BASE, createTaskStream, type ModuleEndpoint } from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";

/* ── Module definitions ─────────────────────────────────────────── */

interface ModuleDef {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
  endpoint: string;
  fields: FieldDef[];
}

interface FieldDef {
  name: string;
  label: string;
  placeholder: string;
  type: "text" | "number" | "checkbox";
  required?: boolean;
  defaultValue?: string | number | boolean;
}

const MODULES: ModuleDef[] = [
  {
    id: "dns-intel",
    label: "DNS Intel",
    description: "Enumerate A/AAAA/MX/NS/TXT/SOA records. Optional subdomain brute-force.",
    icon: Globe,
    endpoint: "/api/dns-intel",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
      { name: "brute_subdomains", label: "Brute-force subdomains", placeholder: "", type: "checkbox", defaultValue: false },
    ],
  },
  {
    id: "cert-transparency",
    label: "Cert Transparency",
    description: "Discover subdomains via crt.sh CT logs — no API key required.",
    icon: Network,
    endpoint: "/api/cert-transparency",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
    ],
  },
  {
    id: "social-hunter",
    label: "Social Hunter",
    description: "Check 50+ platforms for a given username. Keyless enumeration.",
    icon: AtSign,
    endpoint: "/api/social-hunter",
    fields: [
      { name: "username", label: "Username", placeholder: "johndoe", type: "text", required: true },
    ],
  },
  {
    id: "deep-scraper",
    label: "Deep Scraper",
    description: "Recursive extraction: emails, phones, links, documents, social profiles.",
    icon: ScanSearch,
    endpoint: "/api/deep-scraper",
    fields: [
      { name: "url", label: "URL", placeholder: "https://example.com", type: "text", required: true },
      { name: "max_depth", label: "Crawl Depth", placeholder: "2", type: "number", defaultValue: 2 },
      { name: "max_pages", label: "Max Pages", placeholder: "50", type: "number", defaultValue: 50 },
    ],
  },
  {
    id: "whois",
    label: "WHOIS",
    description: "Domain registration — registrar, dates, nameservers, contacts.",
    icon: FileSearch,
    endpoint: "/api/whois",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
    ],
  },
  {
    id: "ssl-analyze",
    label: "SSL Analysis",
    description: "Certificate chain, validity, ciphers, protocol versions, trust grade.",
    icon: Lock,
    endpoint: "/api/ssl-analyze",
    fields: [
      { name: "host", label: "Host", placeholder: "example.com", type: "text", required: true },
      { name: "port", label: "Port", placeholder: "443", type: "number", defaultValue: 443 },
    ],
  },
  {
    id: "http-security",
    label: "HTTP Security",
    description: "CSP, HSTS, X-Frame-Options, CORS, and 10+ security headers.",
    icon: ShieldCheck,
    endpoint: "/api/http-security",
    fields: [
      { name: "url", label: "URL", placeholder: "https://example.com", type: "text", required: true },
    ],
  },
  {
    id: "tech-stack",
    label: "Tech Stack",
    description: "Web server, CMS, JS frameworks, analytics, CDN — Wappalyzer-style.",
    icon: Cpu,
    endpoint: "/api/tech-stack",
    fields: [
      { name: "url", label: "URL", placeholder: "https://example.com", type: "text", required: true },
    ],
  },
  {
    id: "metadata-extract",
    label: "Metadata Extract",
    description: "EXIF, GPS, PDF metadata from images and documents.",
    icon: FileCode2,
    endpoint: "/api/metadata-extract",
    fields: [
      { name: "file_path", label: "File Path", placeholder: "/path/to/image.jpg", type: "text", required: true },
    ],
  },
  {
    id: "ip-geolocation",
    label: "IP Geolocation",
    description: "Locate IP geodata, ASN, ISP and proxy/hosting indicators.",
    icon: MapPin,
    endpoint: "/api/ip-geolocation",
    fields: [{ name: "target", label: "Target", placeholder: "8.8.8.8 or example.com", type: "text", required: true }],
  },
  {
    id: "reverse-ip",
    label: "Reverse IP",
    description: "List co-hosted domains on the same IP.",
    icon: Route,
    endpoint: "/api/reverse-ip",
    fields: [{ name: "target", label: "Target", placeholder: "8.8.8.8 or domain", type: "text", required: true }],
  },
  {
    id: "bgp-asn",
    label: "BGP / ASN",
    description: "BGPView enrichment for IP or ASN intelligence.",
    icon: Radar,
    endpoint: "/api/bgp-asn",
    fields: [{ name: "target", label: "Target", placeholder: "AS15169 or 1.1.1.1", type: "text", required: true }],
  },
  {
    id: "wayback",
    label: "Wayback Machine",
    description: "Historical snapshot enumeration via Archive CDX.",
    icon: Archive,
    endpoint: "/api/wayback",
    fields: [
      { name: "target", label: "Target", placeholder: "example.com", type: "text", required: true },
      { name: "limit", label: "Limit", placeholder: "50", type: "number", defaultValue: 50 },
    ],
  },
  {
    id: "email-header",
    label: "Email Header Analyzer",
    description: "Parse headers for hops, SPF/DKIM/DMARC and origin IPs.",
    icon: MailSearch,
    endpoint: "/api/email-header",
    fields: [{ name: "raw_headers", label: "Raw Headers", placeholder: "Paste RFC822 headers", type: "text", required: true }],
  },
  {
    id: "sherlock",
    label: "Sherlock",
    description: "Deep username hunt across hundreds of platforms.",
    icon: UserCheck,
    endpoint: "/api/sherlock",
    fields: [{ name: "username", label: "Username", placeholder: "torvalds", type: "text", required: true }],
  },
  {
    id: "robots-sitemap",
    label: "Robots & Sitemap",
    description: "Parse robots.txt rules and extract URLs from sitemap.xml — keyless.",
    icon: FileText,
    endpoint: "/api/robots-sitemap",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
      { name: "max_sitemap_urls", label: "Max URLs", placeholder: "200", type: "number", defaultValue: 200 },
    ],
  },
  {
    id: "favicon-hash",
    label: "Favicon Hash",
    description: "Shodan-style MurmurHash3 fingerprint of site favicon.",
    icon: Image,
    endpoint: "/api/favicon-hash",
    fields: [{ name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true }],
  },
  {
    id: "username-permutator",
    label: "Username Permutator",
    description: "Generate username candidates from a name, email, or handle.",
    icon: Shuffle,
    endpoint: "/api/username-permutator",
    fields: [
      { name: "seed", label: "Seed", placeholder: "john.doe or johndoe@mail.com", type: "text", required: true },
      { name: "max_results", label: "Max results", placeholder: "50", type: "number", defaultValue: 50 },
    ],
  },
  {
    id: "github-osint",
    label: "GitHub OSINT",
    description: "Public profile and repos (optional GITHUB_TOKEN for higher limits).",
    icon: Github,
    endpoint: "/api/github-osint",
    fields: [
      { name: "target", label: "Username or org", placeholder: "torvalds", type: "text", required: true },
      { name: "lookup_type", label: "Type (auto/username/org)", placeholder: "auto", type: "text", defaultValue: "auto" },
    ],
  },
  {
    id: "phone-intel",
    label: "Phone Intel",
    description: "Parse number, region, carrier, and timezone via libphonenumber.",
    icon: Phone,
    endpoint: "/api/phone-intel",
    fields: [
      { name: "number", label: "Phone", placeholder: "+14155552671", type: "text", required: true },
      { name: "default_region", label: "Region hint", placeholder: "US", type: "text", defaultValue: "US" },
    ],
  },
  {
    id: "email-reputation",
    label: "Email Reputation",
    description: "Disposable domain check and MX validation — keyless.",
    icon: Mail,
    endpoint: "/api/email-reputation",
    fields: [{ name: "email", label: "Email", placeholder: "user@example.com", type: "text", required: true }],
  },
];

/* ── Per-card state ─────────────────────────────────────────────── */

type CardStatus = "idle" | "loading" | "success" | "error";

interface CardState {
  status: CardStatus;
  values: Record<string, string | number | boolean>;
  result: unknown | null;
  error: string | null;
  taskId: string | null;
}

function initState(mod: ModuleDef): CardState {
  const values: Record<string, string | number | boolean> = {};
  for (const f of mod.fields) {
    values[f.name] = f.defaultValue ?? (f.type === "number" ? 0 : f.type === "checkbox" ? false : "");
  }
  return { status: "idle", values, result: null, error: null, taskId: null };
}

/* ── Component ──────────────────────────────────────────────────── */

interface ModuleCardsProps {
  onStreamLog?: (line: string) => void;
}

export function ModuleCards({ onStreamLog }: ModuleCardsProps) {
  const [cards, setCards] = useState<Record<string, CardState>>(() => {
    const out: Record<string, CardState> = {};
    for (const m of MODULES) out[m.id] = initState(m);
    return out;
  });

  const setField = useCallback((modId: string, field: string, value: string | number | boolean) => {
    setCards((prev) => ({
      ...prev,
      [modId]: { ...prev[modId], values: { ...prev[modId].values, [field]: value } },
    }));
  }, []);

  const initPlaybook = useInvestigationStore((s) => s.initPlaybook);
  const setModuleResult = useInvestigationStore((s) => s.setModuleResult);
  const appendLog = useInvestigationStore((s) => s.appendLog);

  const submit = useCallback(
    async (mod: ModuleDef) => {
      setCards((prev) => ({
        ...prev,
        [mod.id]: { ...prev[mod.id], status: "loading", error: null, result: null, taskId: null },
      }));

      try {
        const body: Record<string, unknown> = {};
        const values = cards[mod.id].values;
        for (const f of mod.fields) {
          body[f.name] = f.type === "number" ? Number(values[f.name]) : values[f.name];
        }

        const data = await runModule(mod.endpoint as ModuleEndpoint, body);
        const taskId = data.task_id;

        // Initialize pseudo-playbook for result viewer
        const pseudoPlaybookId = `tool-${taskId}`;
        initPlaybook(pseudoPlaybookId, mod.label, ["Standalone Tool"], {
          [mod.id]: { module: mod.id, task_id: taskId, status: "pending", label: mod.label }
        });

        setCards((prev) => ({
          ...prev,
          [mod.id]: { ...prev[mod.id], status: "loading", taskId },
        }));

        onStreamLog?.(
          `\x1b[36m[${mod.label}]\x1b[0m Queued → ${taskId ?? "immediate"}`
        );

        if (taskId) {
           createTaskStream(
             taskId,
             (line, parsed) => {
               if (!parsed) return;
               const msgType = parsed.stream || parsed.type;
               if (msgType === "stdout" || msgType === "stderr") {
                 let msg = parsed.data;
                 if (typeof msg !== "string") msg = JSON.stringify(msg);
                 onStreamLog?.(`\x1b[36m[${mod.label}]\x1b[0m ${msg}`);
               }
             },
             (finalResult: any) => {
               setCards((prev) => ({
                 ...prev,
                 [mod.id]: { ...prev[mod.id], status: finalResult?.error ? "error" : "success", result: finalResult },
               }));
               setModuleResult(pseudoPlaybookId, mod.id, finalResult);
               onStreamLog?.(`\x1b[32m[${mod.label}] Completed\x1b[0m`);
             },
             (err) => {
               setCards((prev) => ({
                 ...prev,
                 [mod.id]: { ...prev[mod.id], status: "error", error: err },
               }));
               onStreamLog?.(`\x1b[31m[${mod.label}] Stream Error: ${err}\x1b[0m`);
             }
           );
        } else {
           // Immediate result
           setCards((prev) => ({
             ...prev,
             [mod.id]: { ...prev[mod.id], status: "success", result: data },
           }));
           setModuleResult(pseudoPlaybookId, mod.id, data as unknown as Record<string, unknown>);
        }
      } catch (err) {
        const raw = err instanceof Error ? err.message : String(err);
        const msg = /networkerror|failed to fetch|load failed/i.test(raw)
          ? "Cannot reach backend API. Ensure `npm run dev` is running and backend health is available."
          : raw;
        setCards((prev) => ({
          ...prev,
          [mod.id]: { ...prev[mod.id], status: "error", error: msg },
        }));
        onStreamLog?.(`\x1b[31m[${mod.label}]\x1b[0m ${msg}`);
      }
    },
    [cards, onStreamLog, initPlaybook, setModuleResult]
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
      {MODULES.map((mod) => {
        const card = cards[mod.id];
        const Icon = mod.icon;
        const isLoading = card.status === "loading";

        return (
          <div
            key={mod.id}
            className="soc-panel-dense p-4 flex flex-col gap-3 hover:border-white/10 transition-colors"
          >
            {/* Header */}
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg border border-indigo-500/20 bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                <Icon className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs font-semibold text-slate-200 font-mono">{mod.label}</h3>
                <p className="text-[9px] text-slate-600 leading-relaxed mt-0.5">{mod.description}</p>
              </div>
            </div>

            {/* Fields */}
            <div className="space-y-1.5">
              {mod.fields.map((f) =>
                f.type === "checkbox" ? (
                  <label key={f.name} className="flex items-center gap-2 text-[10px] text-slate-400 cursor-pointer font-mono">
                    <input
                      type="checkbox"
                      checked={!!card.values[f.name]}
                      onChange={(e) => setField(mod.id, f.name, e.target.checked)}
                      className="rounded-sm border-slate-700 bg-slate-900 text-cyan-600 focus:ring-cyan-700 w-3 h-3"
                    />
                    {f.label}
                  </label>
                ) : (
                  <input
                    key={f.name}
                    type={f.type}
                    placeholder={f.placeholder}
                    value={String(card.values[f.name] ?? "")}
                    onChange={(e) =>
                      setField(mod.id, f.name, f.type === "number" ? Number(e.target.value) : e.target.value)
                    }
                    className="w-full soc-input text-xs"
                  />
                )
              )}
            </div>

            {/* Submit */}
            <button
              onClick={() => submit(mod)}
              disabled={isLoading}
              className={cn(
                "mt-auto w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider transition-colors",
                isLoading
                  ? "border border-slate-800 text-slate-600 cursor-wait"
                  : "soc-btn-primary"
              )}
            >
              {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
              {isLoading ? "Running…" : "Run Module"}
            </button>

            {/* Result indicator */}
            {card.status === "success" && (
              <div className="flex items-center gap-1.5 text-[10px] text-emerald-500 font-mono">
                <CheckCircle className="w-3 h-3" />
                {card.taskId ? `Queued – ${card.taskId.slice(0, 8)}…` : "Complete"}
              </div>
            )}
            {card.status === "error" && (
              <div className="flex items-center gap-1.5 text-[10px] text-red-500 font-mono">
                <AlertTriangle className="w-3 h-3" />
                <span className="truncate">{card.error}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
