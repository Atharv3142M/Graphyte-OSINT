"use client";

import React, { useCallback, useEffect, useRef } from "react";
import { Sidebar, type NavItem } from "@/components/Sidebar";
import { Omnibar, type WorkflowIntensity } from "@/components/Omnibar";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { ResizableTerminal } from "@/components/ResizableTerminal";
import { MediaForensicsModal } from "@/components/MediaForensicsModal";
import { ActivityTimelineModal } from "@/components/ActivityTimelineModal";
import { ModuleCards } from "@/components/ModuleCards";
import {
  investigate,
  runModule,
  createTaskStream,
  fetchGraph,
  WS_BASE,
  type ModuleEndpoint,
} from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";
import "@/styles/ansi.css";

/* ── Intensity → endpoint mapping ──────────────────── */
function resolveEndpoint(
  intensity: WorkflowIntensity
): { endpoint: ModuleEndpoint | null; body: Record<string, unknown> } {
  switch (intensity) {
    case "agent":
      return { endpoint: null, body: {} };
    case "low":
    case "standard":
      return { endpoint: "/api/shodan", body: { target: "" } };
    case "aggressive":
      return { endpoint: "/api/port-scan", body: { host: "", ports: [21, 22, 80, 443, 8080] } };
  }
}

export default function Dashboard() {
  const wsRef = useRef<WebSocket | null>(null);

  /* ── UI state (local) ─────────────────────────────── */
  const [navState, setNavState] = React.useState<NavItem>("dashboard");
  const [terminalExpanded, setTerminalExpanded] = React.useState(true);
  const [mediaModalOpen, setMediaModalOpen] = React.useState(false);
  const [timelineModalOpen, setTimelineModalOpen] = React.useState(false);

  /* ── Global store ────────────────────────────────── */
  const loading = useInvestigationStore(
    (s) => s.investigationStatus === "queued" || s.investigationStatus === "running"
  );
  const streamLog = useInvestigationStore((s) => s.streamLog);
  const selectedNode = useInvestigationStore((s) => s.selectedNode);
  const detailPanelOpen = useInvestigationStore((s) => s.detailPanelOpen);
  const investigationStatus = useInvestigationStore((s) => s.investigationStatus);
  const pruneLeaves = useInvestigationStore((s) => s.pruneLeaves);

  /* Store actions */
  const setStatus = useInvestigationStore((s) => s.setStatus);
  const setTaskId = useInvestigationStore((s) => s.setTaskId);
  const setThreadId = useInvestigationStore((s) => s.setThreadId);
  const setThreatScore = useInvestigationStore((s) => s.setThreatScore);
  const setOrchestratorSummary = useInvestigationStore((s) => s.setOrchestratorSummary);
  const appendLog = useInvestigationStore((s) => s.appendLog);
  const clearLog = useInvestigationStore((s) => s.clearLog);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);
  const setSelectedNode = useInvestigationStore((s) => s.setSelectedNode);
  const closeDetailPanel = useInvestigationStore((s) => s.closeDetailPanel);
  const openDetailPanel = useInvestigationStore((s) => s.openDetailPanel);
  const setPruneLeaves = useInvestigationStore((s) => s.setPruneLeaves);

  /* ── Derived ──────────────────────────────────────── */
  const graphVisible = navState === "dashboard" || navState === "graph";

  /* ── Refresh graph from backend ──────────────────── */
  const refreshGraph = useCallback(async () => {
    try {
      const data = await fetchGraph();
      setGraphData(data);
    } catch (e) {
      console.error("Graph refresh failed:", e);
    }
  }, [setGraphData]);

  /* ── Handle investigation ─────────────────────────── */
  const handleInvestigate = useCallback(
    async (target: string, intensity: WorkflowIntensity) => {
      /* Tear down prior WebSocket */
      wsRef.current?.close();
      clearLog();
      setStatus("queued");
      setSelectedNode(null);
      closeDetailPanel();
      setTerminalExpanded(true);

      try {
        /* ── Agent mode: synchronous LangGraph ───────── */
        if (intensity === "agent") {
          appendLog(`\x1b[35m[Agent]\x1b[0m Starting investigation: "${target}"`);
          const res = await investigate(`Investigate ${target}`);
          setThreadId(res.thread_id);
          setThreatScore(res.threat_score);
          setOrchestratorSummary(res.summary ?? null);
          setStatus("done");
          appendLog(
            `\x1b[32m[Agent]\x1b[0m Thread ${res.thread_id} — threat_score: ${res.threat_score}`
          );
          if (res.summary) {
            appendLog(`\x1b[90m${res.summary}\x1b[0m`);
          }
          await refreshGraph();
          return;
        }

        /* ── Celery task mode ──────────────────────── */
        const { endpoint, body } = resolveEndpoint(intensity);
        if (!endpoint) return;

        const payload = {
          ...body,
          target,
          host: target,
          domain: target,
          url: target,
        };

        appendLog(`\x1b[36m[Queue]\x1b[0m Submitting to ${endpoint}…`);
        const res = await runModule(endpoint, payload as Record<string, unknown>);
        const taskId = res.task_id as string;

        setTaskId(taskId);
        setStatus("running");
        appendLog(`\x1b[36m[Task]\x1b[0m ${taskId}`);
        appendLog(`\x1b[90mStream: ${WS_BASE}/ws/task/${taskId}\x1b[0m`);

        /* Open WebSocket stream */
        wsRef.current = createTaskStream(
          taskId,
          (_raw, parsed) => {
            if (!parsed) return;
            const p = parsed as { type?: string; stream?: string; data?: unknown };
            if (p.type === "done") {
              setStatus("done");
              appendLog(`\x1b[32m[DONE]\x1b[0m Task complete`);
              return;
            }
            if (p.type === "result" && p.data) {
              appendLog(`\x1b[32m[Result]\x1b[0m ${JSON.stringify(p.data)}`);
              return;
            }
            if (p.stream && p.data) {
              const prefix = p.stream === "stderr" ? "\x1b[31m" : "\x1b[90m";
              appendLog(`${prefix}[${p.stream}] ${p.data}\x1b[0m`);
              return;
            }
            appendLog(`\x1b[90m${JSON.stringify(p)}\x1b[0m`);
          },
          () => setStatus("done"),
          (err) => {
            setStatus("error");
            appendLog(`\x1b[31m[WS Error]\x1b[0m ${err}`);
          }
        );
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setStatus("error");
        appendLog(`\x1b[31m[Error]\x1b[0m ${msg}`);
      }
    },
    [
      clearLog, setStatus, setTaskId, setThreadId, setThreatScore, setOrchestratorSummary,
      appendLog, closeDetailPanel, refreshGraph, setSelectedNode,
    ]
  );

  /* ── Auto-refresh graph when task completes ─────── */
  useEffect(() => {
    if (investigationStatus === "done") {
      refreshGraph();
    }
  }, [investigationStatus, refreshGraph]);

  /* ── Cleanup WebSocket on unmount ───────────────── */
  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  /* ── Node selection ──────────────────────────────── */
  const handleNodeSelect = useCallback(
    (node: import("@/components/NodeDetailPanel").NodeDetail | null) => {
      if (node) {
        openDetailPanel(node);
      } else {
        closeDetailPanel();
      }
    },
    [openDetailPanel, closeDetailPanel]
  );

  return (
    <div className="h-screen w-screen overflow-hidden relative">
      {/* ── Layer 0: Full-screen Graph ──────────────────── */}
      <div
        className={`absolute inset-0 z-0 ${
          graphVisible ? "" : "pointer-events-none opacity-20"
        }`}
      >
        <GraphCanvas
          pruneLeaves={pruneLeaves}
          onPruneChange={setPruneLeaves}
          onNodeSelect={handleNodeSelect}
          selectedNodeId={selectedNode?.id ?? null}
          className="w-full h-full"
        />
      </div>

      {/* ── Layer 1: Slim icon-rail sidebar ─────────────── */}
      <div className="absolute top-0 left-0 h-full z-30">
        <Sidebar active={navState} onNavigate={setNavState} />
      </div>

      {/* ── Layer 2: Floating Omnibar ───────────────────── */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 w-full max-w-2xl px-4">
        <Omnibar onInvestigate={handleInvestigate} loading={loading} />
      </div>

      {/* ── Layer 3: Secondary content panels ─────────── */}
      {!graphVisible && (
        <div className="absolute inset-0 z-10 ml-[60px] pt-[76px] overflow-hidden">
          <div className="h-full overflow-y-auto p-6">
            {navState === "recon" && (
              <div className="animate-fade-in-up">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">Recon Modules</h2>
                <ModuleCards onStreamLog={(line) => appendLog(line)} />
              </div>
            )}
            {navState === "spatial" && (
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
            {navState === "media" && (
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
            {navState === "reports" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Reports</h3>
                  <p className="text-slate-400 text-sm">
                    Generate and export STIX-compliant reports.
                  </p>
                </div>
              </div>
            )}
            {navState === "settings" && (
              <div className="animate-fade-in-up">
                <div className="glass-panel rounded-2xl p-6 max-w-xl">
                  <h3 className="text-slate-200 font-medium mb-2">Secure Settings</h3>
                  <p className="text-slate-400 text-sm">
                    API keys, credentials, and audit configuration.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Layer 4: Node detail panel (right side) ──── */}
      <NodeDetailPanel
        node={selectedNode}
        onClose={closeDetailPanel}
        isOpen={detailPanelOpen}
      />

      {/* ── Layer 5: Floating terminal (bottom-left) ───── */}
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

      {/* ── Modals ────────────────────────────────────── */}
      <MediaForensicsModal open={mediaModalOpen} onOpenChange={setMediaModalOpen} />
      <ActivityTimelineModal
        open={timelineModalOpen}
        onOpenChange={setTimelineModalOpen}
      />
    </div>
  );
}
