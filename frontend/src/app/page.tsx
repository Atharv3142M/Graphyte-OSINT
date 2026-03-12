"use client";

import { useCallback, useRef, useState } from "react";
import { Sidebar, type NavItem } from "@/components/Sidebar";
import { Omnibar, type WorkflowIntensity } from "@/components/Omnibar";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeDetailPanel, type NodeDetail } from "@/components/NodeDetailPanel";
import { ResizableTerminal } from "@/components/ResizableTerminal";
import { MediaForensicsModal } from "@/components/MediaForensicsModal";
import { ActivityTimelineModal } from "@/components/ActivityTimelineModal";
import { ModuleCards } from "@/components/ModuleCards";
import "@/styles/ansi.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const DEFAULT_TENANT_ID =
  process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

export default function Dashboard() {
  const [nav, setNav] = useState<NavItem>("dashboard");
  const [loading, setLoading] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [pruneLeaves, setPruneLeaves] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [timelineModalOpen, setTimelineModalOpen] = useState(false);
  const [terminalExpanded, setTerminalExpanded] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);

  /* ── Whether the graph is visible (dashboard or graph tab) ─── */
  const graphVisible = nav === "dashboard" || nav === "graph";

  /* ── Investigate handler (unchanged logic) ─────────────────── */
  const handleInvestigate = useCallback(
    async (target: string, intensity: WorkflowIntensity) => {
      setLoading(true);
      setStreamLog([]);
      setTerminalExpanded(true);
      wsRef.current?.close();

      try {
        if (intensity === "agent") {
          const res = await fetch(`${API_BASE}/api/agent/investigate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Tenant-ID": DEFAULT_TENANT_ID,
            },
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
          headers: {
            "Content-Type": "application/json",
            "X-Tenant-ID": DEFAULT_TENANT_ID,
          },
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
    <div className="h-screen w-screen overflow-hidden relative">
      {/* ── Layer 0: Full-screen Graph ──────────────────────── */}
      <div className={`absolute inset-0 z-0 ${graphVisible ? "" : "pointer-events-none opacity-20"}`}>
        <GraphCanvas
          pruneLeaves={pruneLeaves}
          onPruneChange={setPruneLeaves}
          onNodeSelect={handleNodeSelect}
          selectedNodeId={selectedNode?.id ?? null}
          className="w-full h-full"
        />
      </div>

      {/* ── Layer 1: Slim icon-rail sidebar ─────────────────── */}
      <div className="absolute top-0 left-0 h-full z-30">
        <Sidebar active={nav} onNavigate={setNav} />
      </div>

      {/* ── Layer 2: Floating Omnibar ──────────────────────── */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 w-full max-w-2xl px-4">
        <Omnibar onInvestigate={handleInvestigate} loading={loading} />
      </div>

      {/* ── Layer 3: Secondary content panels ──────────────── */}
      {!graphVisible && (
        <div className="absolute inset-0 z-10 ml-[60px] pt-[76px] overflow-hidden">
          <div className="h-full overflow-y-auto p-6">
            {nav === "recon" && (
              <div className="animate-fade-in-up">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">Recon Modules</h2>
                <ModuleCards
                  onStreamLog={(line) => setStreamLog((p) => [...p, line])}
                />
              </div>
            )}
            {nav === "spatial" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Spatial Intelligence</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    Geospatial mapping and location-based threat analysis.
                  </p>
                  <button
                    onClick={() => setTimelineModalOpen(true)}
                    className="gradient-btn px-4 py-2.5 rounded-xl text-white text-sm font-medium transition-all hover:shadow-lg hover:shadow-cyan-500/20"
                  >
                    View Activity Timeline
                  </button>
                </div>
              </div>
            )}
            {nav === "media" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Media Forensics</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    Image analysis with face and object detection.
                  </p>
                  <button
                    onClick={() => setMediaModalOpen(true)}
                    className="gradient-btn px-4 py-2.5 rounded-xl text-white text-sm font-medium transition-all hover:shadow-lg hover:shadow-cyan-500/20"
                  >
                    Open Image Forensics
                  </button>
                </div>
              </div>
            )}
            {nav === "reports" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Reports</h3>
                  <p className="text-slate-400 text-sm">Generate and export STIX-compliant reports.</p>
                </div>
              </div>
            )}
            {nav === "settings" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Secure Settings</h3>
                  <p className="text-slate-400 text-sm">API keys, credentials, and audit configuration.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Layer 4: Node detail panel (right side) ────────── */}
      <NodeDetailPanel
        node={selectedNode}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedNode(null);
        }}
        isOpen={detailPanelOpen}
      />

      {/* ── Layer 5: Floating terminal (bottom-left) ────────── */}
      <div className="absolute bottom-4 left-[72px] z-30 w-[560px] max-w-[calc(100vw-200px)]">
        <ResizableTerminal
          lines={streamLog}
          maxLines={500}
          defaultHeight={200}
          minHeight={100}
          maxHeight={400}
          expanded={terminalExpanded}
          onToggle={() => setTerminalExpanded((v) => !v)}
        />
      </div>

      {/* ── Modals ──────────────────────────────────────────── */}
      <MediaForensicsModal open={mediaModalOpen} onOpenChange={setMediaModalOpen} />
      <ActivityTimelineModal open={timelineModalOpen} onOpenChange={setTimelineModalOpen} />
    </div>
  );
}
