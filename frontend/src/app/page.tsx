"use client";

import { useCallback, useRef, useState } from "react";
import { VirtualTerminal } from "@/components/VirtualTerminal";
import { StixGraph } from "@/components/StixGraph";
import "@/styles/ansi.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

type Tool = "shodan" | "censys" | "scrape" | "port-scan" | null;

export default function Dashboard() {
  const [activeTool, setActiveTool] = useState<Tool>(null);
  const [loading, setLoading] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [finalResult, setFinalResult] = useState<string | null>(null);
  const [pruneLeaves, setPruneLeaves] = useState(false);
  const [activeTab, setActiveTab] = useState<"terminal" | "graph" | "result">("terminal");
  const [form, setForm] = useState({
    target: "",
    urls: "",
    host: "",
    api_key: "",
    api_id: "",
    api_secret: "",
  });
  const wsRef = useRef<WebSocket | null>(null);

  const runRequest = useCallback(async () => {
    setLoading(true);
    setStreamLog([]);
    setFinalResult(null);
    setActiveTab("terminal");
    wsRef.current?.close();

    try {
      let res: Response;
      if (activeTool === "shodan") {
        res = await fetch(`${API_BASE}/api/shodan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: form.target,
            api_key: form.api_key || undefined,
          }),
        });
      } else if (activeTool === "censys") {
        res = await fetch(`${API_BASE}/api/censys`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: form.target,
            api_id: form.api_id || undefined,
            api_secret: form.api_secret || undefined,
          }),
        });
      } else if (activeTool === "scrape") {
        res = await fetch(`${API_BASE}/api/scrape`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            urls: form.urls.split("\n").filter(Boolean),
            max_workers: 5,
          }),
        });
      } else if (activeTool === "port-scan") {
        res = await fetch(`${API_BASE}/api/port-scan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            host: form.host,
            ports: [21, 22, 80, 443, 8080],
            max_workers: 20,
            timeout: 2,
          }),
        });
      } else {
        setLoading(false);
        return;
      }

      const data = await res.json();
      const taskId = data.task_id;
      if (!taskId) {
        setFinalResult(JSON.stringify(data, null, 2));
        setActiveTab("result");
        setLoading(false);
        return;
      }

      const ws = new WebSocket(`${WS_BASE}/ws/task/${taskId}`);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const obj = JSON.parse(ev.data);
          if (obj.type === "done") {
            setLoading(false);
            ws.close();
            wsRef.current = null;
            return;
          }
          if (obj.type === "result" && obj.data) {
            setFinalResult(JSON.stringify(obj.data, null, 2));
            setActiveTab("result");
            return;
          }
          if (obj.stream && obj.data) {
            const prefix = obj.stream === "stderr" ? "\x1b[31m" : "";
            const suffix = obj.stream === "stderr" ? "\x1b[0m" : "";
            setStreamLog((prev) => [...prev, `${prefix}[${obj.stream}] ${obj.data}${suffix}`]);
          }
        } catch {
          setStreamLog((prev) => [...prev, ev.data]);
        }
      };

      ws.onerror = () => {
        setStreamLog((prev) => [...prev, "\x1b[31m[error] WebSocket error\x1b[0m"]);
        setLoading(false);
      };

      ws.onclose = () => {
        setLoading(false);
        wsRef.current = null;
      };
    } catch (e) {
      setFinalResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setActiveTab("result");
      setLoading(false);
    }
  }, [activeTool, form]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="flex-none border-b border-slate-700 px-6 py-4">
        <h1 className="text-xl font-bold text-cyan-400">Unified Enterprise OSINT Platform</h1>
        <p className="mt-1 text-sm text-slate-400">
          Distributed task queue · Real-time stream · STIX graph visualization
        </p>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-72 flex-none border-r border-slate-700 p-4 overflow-y-auto">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Tools</h2>
          <div className="space-y-2">
            {(["shodan", "censys", "scrape", "port-scan"] as const).map((tool) => (
              <button
                key={tool}
                onClick={() => setActiveTool(tool)}
                className={`block w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition ${
                  activeTool === tool ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {tool === "shodan" && "Shodan Recon"}
                {tool === "censys" && "Censys Recon"}
                {tool === "scrape" && "URL Scraper"}
                {tool === "port-scan" && "Port Scanner"}
              </button>
            ))}
          </div>

          {activeTool && (
            <div className="mt-6 space-y-3">
              <h3 className="text-xs font-semibold text-slate-500 uppercase">Input</h3>
              {(activeTool === "shodan" || activeTool === "censys") && (
                <input
                  type="text"
                  placeholder={activeTool === "shodan" ? "IP or domain" : "IPv4"}
                  value={form.target}
                  onChange={(e) => setForm({ ...form, target: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              )}
              {activeTool === "shodan" && (
                <input
                  type="password"
                  placeholder="API key (optional)"
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              )}
              {activeTool === "censys" && (
                <>
                  <input
                    type="text"
                    placeholder="API ID (optional)"
                    value={form.api_id}
                    onChange={(e) => setForm({ ...form, api_id: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                  />
                  <input
                    type="password"
                    placeholder="API secret (optional)"
                    value={form.api_secret}
                    onChange={(e) => setForm({ ...form, api_secret: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                  />
                </>
              )}
              {activeTool === "scrape" && (
                <textarea
                  placeholder="URLs (one per line)"
                  value={form.urls}
                  onChange={(e) => setForm({ ...form, urls: e.target.value })}
                  rows={4}
                  className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              )}
              {activeTool === "port-scan" && (
                <input
                  type="text"
                  placeholder="Hostname or IP"
                  value={form.host}
                  onChange={(e) => setForm({ ...form, host: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              )}
              <button
                onClick={runRequest}
                disabled={loading}
                className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
              >
                {loading ? "Running…" : "Run"}
              </button>
            </div>
          )}
        </aside>

        <main className="flex-1 flex flex-col overflow-hidden p-4">
          <div className="flex items-center gap-4 mb-3">
            <div className="flex rounded-lg border border-slate-700 p-0.5">
              {(["terminal", "graph", "result"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition ${
                    activeTab === tab ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
            {activeTab === "graph" && (
              <label className="flex items-center gap-2 text-sm text-slate-400">
                <input
                  type="checkbox"
                  checked={pruneLeaves}
                  onChange={(e) => setPruneLeaves(e.target.checked)}
                  className="rounded border-slate-600"
                />
                Prune leaf nodes
              </label>
            )}
          </div>

          <div className="flex-1 min-h-0 rounded-xl border border-slate-700 overflow-hidden">
            {activeTab === "terminal" && (
              <div className="h-full flex flex-col">
                <h3 className="text-sm font-medium text-slate-400 px-4 pt-3 pb-1">Live stream</h3>
                <div className="flex-1 min-h-0">
                  <VirtualTerminal lines={streamLog} maxLines={500} className="h-full rounded-none border-0" />
                </div>
              </div>
            )}
            {activeTab === "graph" && (
              <div className="h-full p-2">
                <StixGraph pruneLeaves={pruneLeaves} className="h-full" />
              </div>
            )}
            {activeTab === "result" && (
              <pre className="h-full overflow-auto bg-slate-900 p-4 text-sm text-slate-300 font-mono">
                {finalResult || "No result yet."}
              </pre>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
