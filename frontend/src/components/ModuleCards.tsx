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
    label: "DNS Intelligence",
    description: "Enumerate DNS records (A, AAAA, MX, NS, TXT, SOA, CNAME, SRV) with optional subdomain brute-forcing.",
    icon: Globe,
    endpoint: "/api/dns-intel",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
      { name: "brute_subdomains", label: "Brute-force subdomains", placeholder: "", type: "checkbox", defaultValue: false },
    ],
  },
  {
    id: "whois",
    label: "WHOIS Lookup",
    description: "Domain registration details — registrar, dates, nameservers, registrant contacts.",
    icon: FileSearch,
    endpoint: "/api/whois",
    fields: [
      { name: "domain", label: "Domain", placeholder: "example.com", type: "text", required: true },
    ],
  },
  {
    id: "ssl-analyze",
    label: "SSL / TLS Analysis",
    description: "Certificate chain, validity, cipher suites, protocol versions, and trust score.",
    icon: Lock,
    endpoint: "/api/ssl-analyze",
    fields: [
      { name: "host", label: "Host", placeholder: "example.com", type: "text", required: true },
      { name: "port", label: "Port", placeholder: "443", type: "number", defaultValue: 443 },
    ],
  },
  {
    id: "http-security",
    label: "HTTP Security Headers",
    description: "Analyze Content-Security-Policy, HSTS, X-Frame-Options, CORS, and more.",
    icon: ShieldCheck,
    endpoint: "/api/http-security",
    fields: [
      { name: "url", label: "URL", placeholder: "https://example.com", type: "text", required: true },
    ],
  },
  {
    id: "tech-stack",
    label: "Tech Stack Detection",
    description: "Identify web server, CMS, JavaScript frameworks, analytics, and CDN from fingerprints.",
    icon: Cpu,
    endpoint: "/api/tech-stack",
    fields: [
      { name: "url", label: "URL", placeholder: "https://example.com", type: "text", required: true },
    ],
  },
  {
    id: "metadata-extract",
    label: "Metadata Extraction",
    description: "Extract EXIF, GPS, PDF metadata, and file system info from images and documents.",
    icon: FileCode2,
    endpoint: "/api/metadata-extract",
    fields: [
      { name: "file_path", label: "File Path", placeholder: "/path/to/image.jpg", type: "text", required: true },
    ],
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
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {MODULES.map((mod) => {
        const card = cards[mod.id];
        const Icon = mod.icon;
        const isLoading = card.status === "loading";

        return (
          <div
            key={mod.id}
            className="group rounded-xl border border-slate-700 bg-slate-900/50 p-5 flex flex-col gap-3 hover:border-cyan-500/40 transition-colors"
          >
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Icon className="w-4.5 h-4.5 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">{mod.label}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{mod.description}</p>
              </div>
            </div>

            {/* Fields */}
            <div className="space-y-2">
              {mod.fields.map((f) =>
                f.type === "checkbox" ? (
                  <label key={f.name} className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!card.values[f.name]}
                      onChange={(e) => setField(mod.id, f.name, e.target.checked)}
                      className="rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/30"
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
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-colors"
                  />
                )
              )}
            </div>

            {/* Submit */}
            <button
              onClick={() => submit(mod)}
              disabled={isLoading}
              className={cn(
                "mt-auto w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isLoading
                  ? "bg-slate-800 text-slate-500 cursor-wait"
                  : "bg-cyan-600 hover:bg-cyan-500 text-white"
              )}
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isLoading ? "Running…" : "Run Module"}
            </button>

            {/* Result indicator */}
            {card.status === "success" && (
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <CheckCircle className="w-3.5 h-3.5" />
                {card.taskId ? `Queued – Task ${card.taskId.slice(0, 8)}…` : "Complete"}
              </div>
            )}
            {card.status === "error" && (
              <div className="flex items-center gap-2 text-xs text-red-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                {card.error}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
