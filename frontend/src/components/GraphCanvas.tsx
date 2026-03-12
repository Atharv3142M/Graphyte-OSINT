"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import cytoscape, { Core, NodeSingular } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, Layers, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NodeDetail } from "./NodeDetailPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Color map for node types ──────────────────────────── */
const TYPE_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  default:          { bg: "#06b6d4", border: "#22d3ee", glow: "rgba(6,182,212,0.35)" },
  ipv4_addr:        { bg: "#22c55e", border: "#4ade80", glow: "rgba(34,197,94,0.35)" },
  domain_name:      { bg: "#8b5cf6", border: "#a78bfa", glow: "rgba(139,92,246,0.35)" },
  network_traffic:  { bg: "#f59e0b", border: "#fbbf24", glow: "rgba(245,158,11,0.35)" },
  note:             { bg: "#ec4899", border: "#f472b6", glow: "rgba(236,72,153,0.35)" },
  server:           { bg: "#ef4444", border: "#fca5a5", glow: "rgba(239,68,68,0.45)" },
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

  const runLayout = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.layout({ name: layoutType, animate: true, animationDuration: 400 }).run();
    }
  }, [layoutType]);

  useEffect(() => {
    if (!loading && cyRef.current) runLayout();
  }, [layoutType, loading, runLayout]);

  const loadGraph = useCallback(async () => {
    if (!containerRef.current) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/graph`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const elements = data.elements || { nodes: [], edges: [] };
      let nodes = elements.nodes || [];
      let edges = elements.edges || [];

      if (pruneLeaves && nodes.length > 0) {
        const nodeIds = new Set<string>(nodes.map((n: { data: { id: string } }) => n.data.id));
        const degree = new Map<string, number>();
        nodeIds.forEach((id: string) => degree.set(id, 0));
        edges.forEach((e: { data: { source: string; target: string } }) => {
          degree.set(e.data.source, (degree.get(e.data.source) || 0) + 1);
          degree.set(e.data.target, (degree.get(e.data.target) || 0) + 1);
        });
        const leafIds = new Set([...nodeIds].filter((id) => (degree.get(id) || 0) <= 1));
        const keepIds = new Set([...nodeIds].filter((id) => !leafIds.has(id)));
        nodes = nodes.filter((n: { data: { id: string } }) => keepIds.has(n.data.id));
        edges = edges.filter(
          (e: { data: { source: string; target: string } }) =>
            keepIds.has(e.data.source) && keepIds.has(e.data.target)
        );
      }

      cyRef.current?.destroy();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = cytoscape({
        container: containerRef.current,
        elements: { nodes, edges },
        // shadow-* props are valid Cytoscape CSS but missing from @types/cytoscape
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
          {
            selector: "node.ipv4_addr",
            style: {
              "background-color": TYPE_COLORS.ipv4_addr.bg,
              "border-color": TYPE_COLORS.ipv4_addr.border,
              "shadow-color": TYPE_COLORS.ipv4_addr.glow,
            },
          },
          {
            selector: "node.domain_name",
            style: {
              "background-color": TYPE_COLORS.domain_name.bg,
              "border-color": TYPE_COLORS.domain_name.border,
              "shadow-color": TYPE_COLORS.domain_name.glow,
            },
          },
          {
            selector: "node.network_traffic",
            style: {
              "background-color": TYPE_COLORS.network_traffic.bg,
              "border-color": TYPE_COLORS.network_traffic.border,
              "shadow-color": TYPE_COLORS.network_traffic.glow,
            },
          },
          {
            selector: "node.note",
            style: {
              "background-color": TYPE_COLORS.note.bg,
              "border-color": TYPE_COLORS.note.border,
              "shadow-color": TYPE_COLORS.note.glow,
            },
          },
          {
            selector: "node.server",
            style: {
              "background-color": TYPE_COLORS.server.bg,
              "border-color": TYPE_COLORS.server.border,
              "shadow-color": TYPE_COLORS.server.glow,
              "border-width": 3,
              width: 38,
              height: 38,
            },
          },
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

      cy.on("tap", "node", (evt) => {
        const node = evt.target as NodeSingular;
        const data = node.data();
        const classes = node.classes();
        const isServer = classes.includes("server") || data.type === "ipv4-addr";
        onNodeSelect({
          id: data.id,
          label: data.label,
          type: data.type || (isServer ? "server" : "node"),
          stix: data.stix || {},
          riskScore: data.riskScore ?? (isServer ? 0.65 : 0.2),
          entityResolution: data.entityResolution || {},
          metadata: { ...data },
        });
      });

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
  }, [pruneLeaves, layoutType, onNodeSelect]);

  useEffect(() => {
    loadGraph();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [loadGraph]);

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
