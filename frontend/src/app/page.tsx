"use client";

import { useCallback, useRef, useState } from "react";
import { Sidebar, type NavItem } from "@/components/Sidebar";
import { Omnibar, type WorkflowIntensity } from "@/components/Omnibar";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeDetailPanel, type NodeDetail } from "@/components/NodeDetailPanel";
import { ResizableTerminal } from "@/components/ResizableTerminal";
import { MediaForensicsModal } from "@/components/MediaForensicsModal";
import { ActivityTimelineModal } from "@/components/ActivityTimelineModal";
import "@/styles/ansi.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export default function Dashboard() {
  const [nav, setNav] = useState<NavItem>("dashboard");
  const [loading, setLoading] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [pruneLeaves, setPruneLeaves] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [timelineModalOpen, setTimelineModalOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const handleInvestigate = useCallback(
    async (target: string, intensity: WorkflowIntensity) => {
      setLoading(true);
      setStreamLog([]);
      wsRef.current?.close();

      try {
        if (intensity === "agent") {
          const res = await fetch(`${API_BASE}/api/agent/investigate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal: `Investigate ${target}` }),
          });
          const data = await res.json();
          setStreamLog((p) => [...p, `\x1b[36m[Agent] ${JSON.stringify(data, null, 2)}\x1b[0m`]);
          setLoading(false);
          return;
        }

        let endpoint = "";
        let body: Record<string, unknown> = {};
        if (intensity === "low" || intensity === "standard") {
          endpoint = "/api/shodan";
          body = { target };
        } else if (intensity === "aggressive") {
          endpoint = "/api/port-scan";
          body = { host: target, ports: [21, 22, 80, 443, 8080] };
        } else {
          endpoint = "/api/shodan";
          body = { target };
        }

        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        const taskId = data.task_id;

        if (!taskId) {
          setStreamLog((p) => [...p, `\x1b[32m[Result] ${JSON.stringify(data, null, 2)}\x1b[0m`]);
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
              setStreamLog((p) => [...p, `\x1b[32m[Result] ${JSON.stringify(obj.data, null, 2)}\x1b[0m`]);
              return;
            }
            if (obj.stream && obj.data) {
              const prefix = obj.stream === "stderr" ? "\x1b[31m" : "\x1b[90m";
              setStreamLog((p) => [...p, `${prefix}[${obj.stream}] ${obj.data}\x1b[0m`]);
            }
          } catch {
            setStreamLog((p) => [...p, ev.data]);
          }
        };

        ws.onerror = () => {
          setStreamLog((p) => [...p, "\x1b[31m[error] WebSocket error\x1b[0m"]);
          setLoading(false);
        };

        ws.onclose = () => {
          setLoading(false);
          wsRef.current = null;
        };
      } catch (e) {
        setStreamLog((p) => [...p, `\x1b[31m[Error] ${e instanceof Error ? e.message : String(e)}\x1b[0m`]);
        setLoading(false);
      }
    },
    []
  );

  const handleNodeSelect = useCallback((node: NodeDetail | null) => {
    setSelectedNode(node);
    setDetailPanelOpen(!!node);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar active={nav} onNavigate={setNav} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Omnibar */}
        <header className="flex-none border-b border-slate-800 bg-slate-900/50 px-6 py-4">
          <div className="flex items-center gap-4">
            <Omnibar onInvestigate={handleInvestigate} loading={loading} />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 flex min-h-0 relative">
          <div className="flex-1 flex flex-col min-w-0 p-4 overflow-hidden">
            {nav === "dashboard" && (
              <div className="space-y-4 flex-1 flex flex-col min-h-0">
                <div className="flex-1 min-h-0">
                  <GraphCanvas
                    pruneLeaves={pruneLeaves}
                    onPruneChange={setPruneLeaves}
                    onNodeSelect={handleNodeSelect}
                    selectedNodeId={selectedNode?.id ?? null}
                    className="h-full"
                  />
                </div>
              </div>
            )}
            {nav === "graph" && (
              <div className="flex-1 min-h-0">
                <GraphCanvas
                  pruneLeaves={pruneLeaves}
                  onPruneChange={setPruneLeaves}
                  onNodeSelect={handleNodeSelect}
                  selectedNodeId={selectedNode?.id ?? null}
                  className="h-full"
                />
              </div>
            )}
            {nav === "spatial" && (
              <div className="flex-1 flex flex-col gap-4">
                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6">
                  <h3 className="text-slate-300 font-medium mb-2">Spatial Intelligence</h3>
                  <p className="text-slate-500 text-sm mb-4">
                    Geospatial mapping and location-based threat analysis.
                  </p>
                  <button
                    onClick={() => setTimelineModalOpen(true)}
                    className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium"
                  >
                    View Activity Timeline
                  </button>
                </div>
              </div>
            )}
            {nav === "media" && (
              <div className="flex-1 flex flex-col gap-4">
                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6">
                  <h3 className="text-slate-300 font-medium mb-2">Media Forensics</h3>
                  <p className="text-slate-500 text-sm mb-4">
                    Image analysis with face and object detection.
                  </p>
                  <button
                    onClick={() => setMediaModalOpen(true)}
                    className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium"
                  >
                    Open Image Forensics
                  </button>
                </div>
              </div>
            )}
            {nav === "reports" && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6">
                <h3 className="text-slate-300 font-medium mb-2">Reports</h3>
                <p className="text-slate-500 text-sm">Generate and export STIX-compliant reports.</p>
              </div>
            )}
            {nav === "settings" && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6">
                <h3 className="text-slate-300 font-medium mb-2">Secure Settings</h3>
                <p className="text-slate-500 text-sm">API keys, credentials, and audit configuration.</p>
              </div>
            )}
          </div>

          {/* Progressive disclosure detail panel */}
          <NodeDetailPanel
            node={selectedNode}
            onClose={() => {
              setDetailPanelOpen(false);
              setSelectedNode(null);
            }}
            isOpen={detailPanelOpen}
          />
        </main>

        {/* Resizable terminal */}
        <div className="flex-none">
          <ResizableTerminal
            lines={streamLog}
            maxLines={500}
            defaultHeight={220}
            minHeight={120}
            maxHeight={480}
          />
        </div>
      </div>

      <MediaForensicsModal open={mediaModalOpen} onOpenChange={setMediaModalOpen} />
      <ActivityTimelineModal open={timelineModalOpen} onOpenChange={setTimelineModalOpen} />
    </div>
  );
}
