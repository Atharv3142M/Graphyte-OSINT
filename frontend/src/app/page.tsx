"use client";

import { useCallback, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

type Tool = "shodan" | "censys" | "scrape" | "port-scan" | null;

export default function Home() {
  const [activeTool, setActiveTool] = useState<Tool>(null);
  const [loading, setLoading] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [finalResult, setFinalResult] = useState<string | null>(null);
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
            return;
          }
          if (obj.stream && obj.data) {
            setStreamLog((prev) => [...prev, `[${obj.stream}] ${obj.data}`]);
          }
        } catch {
          setStreamLog((prev) => [...prev, ev.data]);
        }
      };

      ws.onerror = () => {
        setStreamLog((prev) => [...prev, "[error] WebSocket error"]);
        setLoading(false);
      };

      ws.onclose = () => {
        setLoading(false);
        wsRef.current = null;
      };
    } catch (e) {
      setFinalResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setLoading(false);
    }
  }, [activeTool, form]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <header className="border-b border-slate-700 pb-6 mb-8">
        <h1 className="text-2xl font-bold text-cyan-400">
          Unified Enterprise OSINT Platform
        </h1>
        <p className="mt-2 text-slate-400">
          Distributed task queue · Real-time stream · WebSocket
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {(["shodan", "censys", "scrape", "port-scan"] as const).map((tool) => (
          <button
            key={tool}
            onClick={() => setActiveTool(tool)}
            className={`px-4 py-3 rounded-lg font-medium transition ${
              activeTool === tool
                ? "bg-cyan-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
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
        <section className="bg-slate-900 rounded-xl p-6 border border-slate-700 mb-8">
          <h2 className="text-lg font-semibold mb-4">
            {activeTool === "shodan" && "Shodan Lookup (IP or Domain)"}
            {activeTool === "censys" && "Censys Lookup (IPv4)"}
            {activeTool === "scrape" && "Scrape URLs for Emails & Phones"}
            {activeTool === "port-scan" && "TCP Port Scan"}
          </h2>
          <div className="flex flex-col gap-4 max-w-xl">
            {(activeTool === "shodan" || activeTool === "censys") && (
              <input
                type="text"
                placeholder={activeTool === "shodan" ? "IP or domain" : "IPv4 address"}
                value={form.target}
                onChange={(e) => setForm({ ...form, target: e.target.value })}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
              />
            )}
            {activeTool === "shodan" && (
              <input
                type="password"
                placeholder="Shodan API key (optional)"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
              />
            )}
            {activeTool === "censys" && (
              <>
                <input
                  type="text"
                  placeholder="Censys API ID (optional)"
                  value={form.api_id}
                  onChange={(e) => setForm({ ...form, api_id: e.target.value })}
                  className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
                />
                <input
                  type="password"
                  placeholder="Censys API secret (optional)"
                  value={form.api_secret}
                  onChange={(e) => setForm({ ...form, api_secret: e.target.value })}
                  className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
                />
              </>
            )}
            {activeTool === "scrape" && (
              <textarea
                placeholder="URLs (one per line)"
                value={form.urls}
                onChange={(e) => setForm({ ...form, urls: e.target.value })}
                rows={4}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
              />
            )}
            {activeTool === "port-scan" && (
              <input
                type="text"
                placeholder="Hostname or IP"
                value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
              />
            )}
            <button
              onClick={runRequest}
              disabled={loading}
              className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 px-4 py-2 rounded font-medium"
            >
              {loading ? "Running…" : "Run"}
            </button>
          </div>
        </section>
      )}

      {streamLog.length > 0 && (
        <section className="bg-slate-900 border border-slate-700 rounded-xl p-4 mb-8">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">Stream</h3>
          <pre className="text-xs text-slate-300 overflow-auto max-h-40 font-mono">
            {streamLog.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </pre>
        </section>
      )}

      {finalResult && (
        <pre className="bg-slate-900 border border-slate-700 rounded-xl p-6 overflow-auto text-sm text-slate-300">
          {finalResult}
        </pre>
      )}
    </main>
  );
}
