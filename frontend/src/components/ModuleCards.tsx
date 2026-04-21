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
  UserSearch,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { runModule, WS_BASE, type ModuleEndpoint } from "@/lib/api";

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
    icon: UserSearch,
    endpoint: "/api/sherlock",
    fields: [{ name: "username", label: "Username", placeholder: "torvalds", type: "text", required: true }],
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

        setCards((prev) => ({
          ...prev,
          [mod.id]: { ...prev[mod.id], status: "success", result: data, taskId },
        }));

        onStreamLog?.(
          `\x1b[36m[${mod.label}]\x1b[0m Queued → ${taskId ?? "immediate"} \x1b[90m${WS_BASE}/ws/task/${taskId}\x1b[0m`
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setCards((prev) => ({
          ...prev,
          [mod.id]: { ...prev[mod.id], status: "error", error: msg },
        }));
        onStreamLog?.(`\x1b[31m[${mod.label}]\x1b[0m ${msg}`);
      }
    },
    [cards, onStreamLog]
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
            className="border border-slate-800 bg-slate-950/60 p-4 flex flex-col gap-3 hover:border-slate-700 transition-colors"
          >
            {/* Header */}
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 border border-cyan-900 bg-cyan-950/40 flex items-center justify-center flex-shrink-0">
                <Icon className="w-3.5 h-3.5 text-cyan-600" />
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
