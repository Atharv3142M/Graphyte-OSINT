"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import cytoscape, { Core, NodeSingular } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, Layers, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NodeDetail } from "./NodeDetailPanel";
import { fetchGraph } from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";

/* ── Color map for node types ──────────────────────────── */
const TYPE_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  default:          { bg: "#06b6d4", border: "#22d3ee", glow: "rgba(6,182,212,0.35)" },
  ipv4_addr:        { bg: "#22c55e", border: "#4ade80", glow: "rgba(34,197,94,0.35)" },
  "ipv4-addr":      { bg: "#22c55e", border: "#4ade80", glow: "rgba(34,197,94,0.35)" },
  domain_name:      { bg: "#8b5cf6", border: "#a78bfa", glow: "rgba(139,92,246,0.35)" },
  "domain":         { bg: "#8b5cf6", border: "#a78bfa", glow: "rgba(139,92,246,0.35)" },
  network_traffic:  { bg: "#f59e0b", border: "#fbbf24", glow: "rgba(245,158,11,0.35)" },
  note:             { bg: "#ec4899", border: "#f472b6", glow: "rgba(236,72,153,0.35)" },
  server:           { bg: "#ef4444", border: "#fca5a5", glow: "rgba(239,68,68,0.45)" },
  url:              { bg: "#14b8a6", border: "#2dd4bf", glow: "rgba(20,184,166,0.35)" },
  file:             { bg: "#f97316", border: "#fb923c", glow: "rgba(249,115,22,0.35)" },
  email_addr:       { bg: "#a855f7", border: "#c084fc", glow: "rgba(168,85,247,0.35)" },
  vulnerability:    { bg: "#ef4444", border: "#fca5a5", glow: "rgba(239,68,68,0.45)" },
};

interface GraphCanvasProps {
  className?: string;
  pruneLeaves: boolean;
  onPruneChange: (v: boolean) => void;
  onNodeSelect: (node: NodeDetail | null) => void;
  selectedNodeId: string | null;
}

export function GraphCanvas({
  className = "",
  pruneLeaves,
  onPruneChange,
  onNodeSelect,
  selectedNodeId,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layoutType, setLayoutType] = useState<"cose" | "circle">("cose");

  const graphData = useInvestigationStore((s) => s.graphData);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);

  const runLayout = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.layout({ name: layoutType, animate: true, animationDuration: 400 }).run();
    }
  }, [layoutType]);

  useEffect(() => {
    if (!loading && cyRef.current) runLayout();
  }, [layoutType, loading, runLayout]);

  /* ── Load graph from backend ─────────────────────── */
  const loadGraph = useCallback(async () => {
    if (!containerRef.current) return;
    setLoading(true);
    setError(null);
    try {
      let data;

      /* Prefer live store data if present */
      if (graphData && graphData.nodes.length > 0) {
        data = graphData;
      } else {
        data = await fetchGraph();
        setGraphData(data);
      }

      /* Backend returns { elements: { nodes, edges } } — unwrap */
      const elements = "elements" in data
        ? (data as { elements: { nodes: unknown[]; edges: unknown[] } }).elements
        : data as { nodes: unknown[]; edges: unknown[] };
      let nodes = elements.nodes || [];
      let edges = elements.edges || [];

      /* Prune leaf nodes (degree ≤ 1) on demand */
      if (pruneLeaves && nodes.length > 0) {
        const nodeIds = new Set<string>(
          (nodes as { data: { id: string } }[]).map((n) => n.data.id)
        );
        const degree = new Map<string, number>();
        nodeIds.forEach((id: string) => degree.set(id, 0));
        (edges as { data: { source: string; target: string } }[]).forEach((e) => {
          degree.set(e.data.source, (degree.get(e.data.source) || 0) + 1);
          degree.set(e.data.target, (degree.get(e.data.target) || 0) + 1);
        });
        const keepIds = new Set(
          [...nodeIds].filter((id) => (degree.get(id) || 0) > 1)
        );
        nodes = (nodes as { data: { id: string } }[]).filter((n) =>
          keepIds.has(n.data.id)
        );
        edges = (edges as { data: { source: string; target: string } }[]).filter(
          (e) => keepIds.has(e.data.source) && keepIds.has(e.data.target)
        );
      }

      /* Destroy existing instance */
      cyRef.current?.destroy();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = cytoscape({
        container: containerRef.current,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        elements: { nodes, edges } as any,
        style: ([
          /* ── Default nodes: cyan glow ──────────────────── */
          {
            selector: "node",
            style: {
              "background-color": TYPE_COLORS.default.bg,
              "border-width": 2,
              "border-color": TYPE_COLORS.default.border,
              "border-opacity": 0.6,
              label: "data(label)",
              "text-valign": "bottom",
              "text-halign": "center",
              "font-size": "9px",
              "font-family": "Inter, system-ui, sans-serif",
              color: "#cbd5e1",
              "text-margin-y": 6,
              "text-outline-color": "#0f172a",
              "text-outline-width": 2,
              width: 32,
              height: 32,
              "overlay-padding": 6,
              "shadow-blur": 16,
              "shadow-color": TYPE_COLORS.default.glow,
              "shadow-offset-x": 0,
              "shadow-offset-y": 0,
              "shadow-opacity": 0.8,
            },
          },
          /* ── Type-specific nodes ───────────────────────── */
          ...Object.entries(TYPE_COLORS).map(([type, colors]) => ({
            selector: `node.${type}`,
            style: {
              "background-color": colors.bg,
              "border-color": colors.border,
              "shadow-color": colors.glow,
            },
          })),
          /* ── Selected / highlighted ────────────────────── */
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#22d3ee",
              "shadow-blur": 28,
              "shadow-opacity": 1,
              width: 40,
              height: 40,
            },
          },
          {
            selector: "node.highlighted",
            style: {
              "border-width": 3,
              "border-color": "#22d3ee",
              "shadow-blur": 24,
              "shadow-opacity": 1,
            },
          },
          /* ── Edges ─────────────────────────────────────── */
          {
            selector: "edge",
            style: {
              "line-color": "#334155",
              "target-arrow-color": "#475569",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              width: 1.5,
              opacity: 0.4,
            },
          },
          {
            selector: "edge:selected, edge.highlighted",
            style: {
              "line-color": "#06b6d4",
              "target-arrow-color": "#06b6d4",
              opacity: 0.9,
              width: 2,
            },
          },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ] as any),
        layout: {
          name: "cose",
          animate: nodes.length < 500,
          animationDuration: 400,
        },
        minZoom: 0.1,
        maxZoom: 4,
        wheelSensitivity: 0.3,
      });

      /* Node tap → open detail panel */
      cy.on("tap", "node", (evt) => {
        const node = evt.target as NodeSingular;
        const data = node.data();
        const nodeType = data.type || node.classes()[0] || "node";
        onNodeSelect({
          id: data.id,
          label: data.label,
          type: nodeType,
          stix: data.stix || {},
          riskScore: data.riskScore ?? 0.2,
          entityResolution: data.entityResolution || {},
          metadata: { ...data },
        });
      });

      /* Background tap → deselect */
      cy.on("tap", (evt) => {
        if (evt.target === cy) onNodeSelect(null);
      });

      cyRef.current = cy;
      setNodeCount(cy.nodes().length);
      setEdgeCount(cy.edges().length);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [pruneLeaves, layoutType, onNodeSelect, graphData, setGraphData]);

  /* ── Load on mount; re-load when investigation completes ── */
  useEffect(() => {
    loadGraph();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [loadGraph]);

  /* ── Sync selected node highlight in Cytoscape ──── */
  useEffect(() => {
    if (!cyRef.current) return;
    cyRef.current.nodes().unselect();
    if (selectedNodeId) {
      cyRef.current.$(`#${selectedNodeId}`).select();
    }
  }, [selectedNodeId]);

  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
  const fit = () => cyRef.current?.fit(undefined, 50);

  return (
    <div className={cn("relative overflow-hidden", className)}>
      {/* Loading skeleton */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
            <span className="text-sm text-slate-500">Loading graph…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="glass-panel rounded-2xl px-6 py-4 max-w-sm text-center">
            <AlertTriangle className="w-5 h-5 text-red-400 mx-auto mb-2" />
            <span className="text-red-400 text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Live indicator */}
      {!loading && !error && (
        <div className="absolute top-4 right-4 z-20">
          <div className="glass-panel rounded-xl px-3 py-1.5 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-slate-400 font-medium">Live</span>
          </div>
        </div>
      )}

      {/* Cytoscape container */}
      <div ref={containerRef} className="w-full h-full" />

      {/* ── Floating toolbar (bottom-right) ─────────────── */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 z-20">
        <button
          onClick={zoomIn}
          className="p-2 rounded-xl glass-panel hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-all"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          className="p-2 rounded-xl glass-panel hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-all"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={fit}
          className="p-2 rounded-xl glass-panel hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-all"
          title="Fit to view"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        <div className="w-px h-5 bg-white/10 mx-1" />
        <button
          onClick={() => setLayoutType((l) => (l === "cose" ? "circle" : "cose"))}
          className={cn(
            "p-2 rounded-xl glass-panel hover:bg-white/10 transition-all",
            layoutType === "cose" ? "text-cyan-400" : "text-slate-400"
          )}
          title={layoutType === "cose" ? "Switch to circle" : "Switch to force-directed"}
        >
          <Layers className="w-4 h-4" />
        </button>
        <label className="flex items-center gap-2 px-3 py-2 rounded-xl glass-panel cursor-pointer text-slate-400 hover:text-slate-200 transition-all">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px]">Prune</span>
          <input
            type="checkbox"
            checked={pruneLeaves}
            onChange={(e) => onPruneChange(e.target.checked)}
            className="rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-cyan-500 w-3 h-3"
          />
        </label>
      </div>

      {/* ── Stats badge (bottom-left) ──────────────────── */}
      <div className="absolute bottom-4 left-4 z-20">
        <div className="glass-panel rounded-xl px-3 py-1.5 flex items-center gap-3">
          <span className="text-[11px] text-slate-500 font-medium">{nodeCount} nodes</span>
          <span className="w-px h-3 bg-white/10" />
          <span className="text-[11px] text-slate-500 font-medium">{edgeCount} edges</span>
        </div>
      </div>
    </div>
  );
}
