"use client";

import { useState, useCallback } from "react";
import {
  Key,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Database,
  Globe,
  Server,
  Lock,
  Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ─────────────────────────────────────────── */

interface EnvVar {
  key: string;
  value: string;
  description: string;
  masked: boolean;
  category: "api" | "database" | "service" | "celery" | "frontend" | "internal";
}

interface SaveState {
  [key: string]: "idle" | "saving" | "saved" | "error";
}

/* ── Default env vars to display ──────────────────── */

const DEFAULT_VARS: EnvVar[] = [
  { key: "VAULT_SHODAN_API_KEY", value: "", description: "Shodan API key for host enrichment", masked: true, category: "api" },
  { key: "VAULT_CENSYS_API_ID", value: "", description: "Censys API ID for certificate enrichment", masked: true, category: "api" },
  { key: "VAULT_CENSYS_API_SECRET", value: "", description: "Censys API secret", masked: true, category: "api" },
  { key: "CELERY_BROKER_URL", value: "redis://localhost:6379/0", description: "Redis URL for Celery broker", masked: false, category: "celery" },
  { key: "REDIS_URL", value: "redis://localhost:6379/0", description: "Redis URL for pub/sub", masked: false, category: "celery" },
  { key: "NEO4J_URI", value: "bolt://localhost:7687", description: "Neo4j Bolt URI", masked: false, category: "database" },
  { key: "NEO4J_USER", value: "neo4j", description: "Neo4j username", masked: false, category: "database" },
  { key: "NEO4J_PASSWORD", value: "dev_neo4j_secret", description: "Neo4j password", masked: true, category: "database" },
  { key: "WEAVIATE_HTTP_URI", value: "http://localhost:8080", description: "Weaviate URL for semantic search", masked: false, category: "service" },
  { key: "RABBITMQ_URL", value: "amqp://admin:dev_rabbitmq_secret@localhost:5672/", description: "RabbitMQ AMQP URL", masked: false, category: "service" },
  { key: "CELERY_TASK_HARD_TIMEOUT", value: "300", description: "Seconds before Celery task is killed", masked: false, category: "celery" },
  { key: "NEXT_PUBLIC_API_URL", value: "http://localhost:8000", description: "Frontend → API URL", masked: false, category: "frontend" },
  { key: "NEXT_PUBLIC_DEFAULT_TENANT_ID", value: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", description: "Multi-tenant header value", masked: false, category: "frontend" },
];

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  api: Key,
  database: Database,
  service: Globe,
  celery: Cpu,
  frontend: Server,
  internal: Lock,
};

const CATEGORY_LABELS: Record<string, string> = {
  api: "API Keys",
  database: "Databases",
  service: "Services",
  celery: "Celery",
  frontend: "Frontend",
  internal: "Internal",
};

export default function SettingsPage() {
  const [envVars, setEnvVars] = useState<EnvVar[]>(DEFAULT_VARS);
  const [saveStates, setSaveStates] = useState<SaveState>({});
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [testResults, setTestResults] = useState<Record<string, "ok" | "fail" | null>>({});
  const [loadingEnv, setLoadingEnv] = useState(false);

  // Load current env vars from backend
  const loadEnvVars = useCallback(async () => {
    setLoadingEnv(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings/env`, {
        headers: { "X-Tenant-ID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" },
      });
      if (res.ok) {
        const data = await res.json();
        const env: Record<string, string> = data.env_vars || {};
        setEnvVars((prev) =>
          prev.map((v) => ({
            ...v,
            value: env[v.key] !== undefined ? env[v.key] : v.value,
          }))
        );
      }
    } catch {
      // Backend may not support this endpoint yet — silently skip
    } finally {
      setLoadingEnv(false);
    }
  }, []);

  // Save a single env var
  const saveVar = useCallback(async (varKey: string, varValue: string) => {
    setSaveStates((prev) => ({ ...prev, [varKey]: "saving" }));
    try {
      const res = await fetch(`${API_BASE}/api/settings/env`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-ID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        },
        body: JSON.stringify({ key: varKey, value: varValue }),
      });
      if (res.ok) {
        setSaveStates((prev) => ({ ...prev, [varKey]: "saved" }));
        setTimeout(() => setSaveStates((prev) => ({ ...prev, [varKey]: "idle" })), 2000);
      } else {
        setSaveStates((prev) => ({ ...prev, [varKey]: "error" }));
      }
    } catch {
      setSaveStates((prev) => ({ ...prev, [varKey]: "error" }));
    }
  }, []);

  // Test connectivity to a service
  const testService = useCallback(async (service: string) => {
    setTestResults((prev) => ({ ...prev, [service]: null }));
    try {
      let endpoint = "";
      if (service === "neo4j") endpoint = "/api/graph";
      else if (service === "redis") endpoint = "/health";
      else if (service === "api") endpoint = "/health";

      const res = await fetch(`${API_BASE}${endpoint}`);
      setTestResults((prev) => ({ ...prev, [service]: res.ok ? "ok" : "fail" }));
    } catch {
      setTestResults((prev) => ({ ...prev, [service]: "fail" }));
    }
  }, []);

  const toggleVisible = (key: string) => {
    setVisibleKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const grouped = DEFAULT_VARS.reduce<Record<string, EnvVar[]>>((acc, v) => {
    if (!acc[v.category]) acc[v.category] = [];
    acc[v.category].push(v);
    return acc;
  }, {});

  const getSaveState = (key: string) => saveStates[key] ?? "idle";

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-4 max-w-4xl mx-auto space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold text-slate-100 uppercase tracking-widest">Settings</h1>
            <p className="text-[10px] text-slate-600 mt-0.5">Configure API keys, environment variables, and service endpoints</p>
          </div>
          <button
            onClick={loadEnvVars}
            disabled={loadingEnv}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] text-slate-500 border border-slate-800 hover:text-slate-300 hover:border-slate-700 transition-colors"
          >
            <RefreshCw className={cn("w-3 h-3", loadingEnv && "animate-spin")} />
            Sync from Backend
          </button>
        </div>

        {/* Service Status Row */}
        <div className="soc-panel p-3">
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">Service Connectivity</div>
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "api", label: "API Gateway" },
              { id: "neo4j", label: "Neo4j" },
              { id: "redis", label: "Redis" },
            ].map((svc) => (
              <button
                key={svc.id}
                onClick={() => testService(svc.id)}
                className="flex items-center gap-1.5 px-2.5 py-1 border border-slate-800 hover:border-slate-700 transition-colors text-[10px]"
              >
                <div className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  testResults[svc.id] === "ok" ? "bg-emerald-500" :
                  testResults[svc.id] === "fail" ? "bg-red-500" :
                  "bg-slate-700"
                )} />
                <span className="text-slate-400 font-mono">{svc.label}</span>
                {testResults[svc.id] === "ok" && <CheckCircle className="w-3 h-3 text-emerald-500" />}
                {testResults[svc.id] === "fail" && <AlertTriangle className="w-3 h-3 text-red-500" />}
              </button>
            ))}
          </div>
        </div>

        {/* API Keys Section */}
        {grouped["api"] && grouped["api"].length > 0 && (
          <div className="soc-panel p-4">
            <div className="flex items-center gap-2 mb-3">
              <Key className="w-3 h-3 text-cyan-600" />
              <h2 className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">API Keys</h2>
            </div>
            <div className="space-y-2">
              {grouped["api"].map((v) => (
                <div key={v.key} className="flex items-center gap-2 p-2 border border-slate-800/60 bg-slate-950/40">
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-mono text-cyan-500">{v.key}</div>
                    <div className="text-[9px] text-slate-600 mt-0.5">{v.description}</div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <input
                      type={visibleKeys.has(v.key) ? "text" : "password"}
                      value={v.value}
                      onChange={(e) => setEnvVars((prev) => prev.map((x) => x.key === v.key ? { ...x, value: e.target.value } : x))}
                      placeholder="not set"
                      className="w-48 soc-input text-[10px]"
                    />
                    <button
                      onClick={() => toggleVisible(v.key)}
                      className="p-1 text-slate-600 hover:text-slate-400 transition-colors"
                    >
                      {visibleKeys.has(v.key) ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      onClick={() => saveVar(v.key, v.value)}
                      disabled={getSaveState(v.key) === "saving"}
                      className={cn(
                        "px-2 py-1 text-[9px] font-semibold uppercase tracking-wider border transition-colors",
                        getSaveState(v.key) === "saved"
                          ? "border-emerald-900 text-emerald-500"
                          : getSaveState(v.key) === "error"
                          ? "border-red-900 text-red-500"
                          : "border-cyan-900 text-cyan-600 hover:bg-cyan-950"
                      )}
                    >
                      {getSaveState(v.key) === "saving" ? "..." : getSaveState(v.key) === "saved" ? "OK" : "Save"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Environment Variables by Category */}
        {Object.entries(grouped).filter(([cat]) => cat !== "api").map(([category, vars]) => {
          const Icon = CATEGORY_ICONS[category] ?? Server;
          return (
            <div key={category} className="soc-panel p-4">
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-3 h-3 text-slate-500" />
                <h2 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                  {CATEGORY_LABELS[category] ?? category}
                </h2>
              </div>
              <div className="space-y-1.5">
                {vars.map((v) => (
                  <div key={v.key} className="flex items-center gap-2 p-2 border border-slate-800/40 bg-slate-950/30">
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-mono text-slate-400">{v.key}</div>
                      <div className="text-[9px] text-slate-700 mt-0.5">{v.description}</div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {v.masked ? (
                        <>
                          <input
                            type={visibleKeys.has(v.key) ? "text" : "password"}
                            value={v.value}
                            onChange={(e) => setEnvVars((prev) => prev.map((x) => x.key === v.key ? { ...x, value: e.target.value } : x))}
                            placeholder="not set"
                            className="w-40 soc-input text-[10px]"
                          />
                          <button onClick={() => toggleVisible(v.key)} className="p-1 text-slate-600 hover:text-slate-400 transition-colors">
                            {visibleKeys.has(v.key) ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </button>
                        </>
                      ) : (
                        <input
                          type="text"
                          value={v.value}
                          onChange={(e) => setEnvVars((prev) => prev.map((x) => x.key === v.key ? { ...x, value: e.target.value } : x))}
                          className="w-48 soc-input text-[10px]"
                        />
                      )}
                      <button
                        onClick={() => saveVar(v.key, v.value)}
                        disabled={getSaveState(v.key) === "saving"}
                        className={cn(
                          "px-2 py-1 text-[9px] font-semibold uppercase tracking-wider border transition-colors",
                          getSaveState(v.key) === "saved"
                            ? "border-emerald-900 text-emerald-500"
                            : getSaveState(v.key) === "error"
                            ? "border-red-900 text-red-500"
                            : "border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-400"
                        )}
                      >
                        {getSaveState(v.key) === "saving" ? "..." : getSaveState(v.key) === "saved" ? "OK" : "Save"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {/* Info */}
        <div className="soc-panel p-3 border-amber-900/30">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3 h-3 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-[9px] text-slate-500 leading-relaxed">
              API keys are stored server-side in environment variables or a vault. Changes require backend restart to take effect.
              For production deployments, use a vault solution (HashiCorp Vault, AWS Secrets Manager) rather than environment variable files.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
