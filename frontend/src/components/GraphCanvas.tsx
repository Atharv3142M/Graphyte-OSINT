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
  ipv4_addr:       { bg: "#22c55e", border: "#4ade80", glow: "rgba(34,197,94,0.35)" },
  "ipv4-addr":     { bg: "#22c55e", border: "#4ade80", glow: "rgba(34,197,94,0.35)" },
  domain_name:     { bg: "#8b5cf6", border: "#a78bfa", glow: "rgba(139,92,246,0.35)" },
  "domain":        { bg: "#8b5cf6", border: "#a78bfa", glow: "rgba(139,92,246,0.35)" },
  network_traffic: { bg: "#f59e0b", border: "#fbbf24", glow: "rgba(245,158,11,0.35)" },
  "network-traffic":{ bg: "#f59e0b", border: "#fbbf24", glow: "rgba(245,158,11,0.35)" },
  note:            { bg: "#ec4899", border: "#f472b6", glow: "rgba(236,72,153,0.35)" },
  server:          { bg: "#ef4444", border: "#fca5a5", glow: "rgba(239,68,68,0.45)" },
  url:             { bg: "#14b8a6", border: "#2dd4bf", glow: "rgba(20,184,166,0.35)" },
  file:            { bg: "#f97316", border: "#fb923c", glow: "rgba(249,115,22,0.35)" },
  email_addr:      { bg: "#a855f7", border: "#c084fc", glow: "rgba(168,85,247,0.35)" },
  vulnerability:   { bg: "#ef4444", border: "#fca5a5", glow: "rgba(239,68,68,0.45)" },
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
  const [graphEmpty, setGraphEmpty] = useState(false);

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

      /* Use store data if it has nodes */
      if (graphData && graphData.nodes && graphData.nodes.length > 0) {
        data = graphData;
      } else {
        /* Fetch fresh from Neo4j */
        data = await fetchGraph();
        /* Store it so other components can use it */
        setGraphData(data);
      }

      /* Backend returns { elements: { nodes, edges } } — unwrap */
      const elements = "elements" in data
        ? (data as { elements: { nodes: unknown[]; edges: unknown[] } }).elements
        : data as { nodes: unknown[]; edges: unknown[] };
      const rawNodes = elements?.nodes ?? [];
      const rawEdges = elements?.edges ?? [];

      /* Prune leaf nodes (degree ≤ 1) on demand */
      let nodes = rawNodes;
      let edges = rawEdges;
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

      /* Destroy existing instance before creating new one */
      cyRef.current?.destroy();
      cyRef.current = null;
      setNodeCount(0);
      setEdgeCount(0);
      setGraphEmpty(false);

      /* If no nodes at all — show empty state */
      if (nodes.length === 0) {
        setLoading(false);
        setGraphEmpty(true);
        return;
      }

      /* Build Cytoscape instance */
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
              "font-family": "Monaco, 'Courier New', monospace",
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
        const nodeType = data.type || node.classes()[0] || "default";
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
      setGraphEmpty(cy.nodes().length === 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [pruneLeaves, layoutType, onNodeSelect, graphData, setGraphData]);

  /* ── Load on mount only; live graph patches use cy.add()/cy.remove() ── */
  useEffect(() => {
    loadGraph();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
    // loadGraph is stable via useCallback — intentionally run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Live graph patching: add new nodes/edges without remounting ── */
  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return;

    /* No cytoscape instance yet — create it from current graphData */
    if (!cyRef.current) {
      loadGraph();
      return;
    }

    /* Patch existing instance with new nodes/edges */
    const existingNodeIds = new Set(cyRef.current.nodes().map((n) => n.id()));
    const newNodes = graphData.nodes.filter((n) => !existingNodeIds.has(n.data?.id));
    const newEdges = graphData.edges.filter(
      (e) =>
        existingNodeIds.has(e.data?.source) &&
        existingNodeIds.has(e.data?.target) &&
        !cyRef.current!.edges().some((ce) => (ce as cytoscape.EdgeSingular).id() === e.data?.id)
    );

    if (newNodes.length > 0 || newEdges.length > 0) {
      const existingZoom = cyRef.current.zoom();
      const existingPan = cyRef.current.pan();
      if (newNodes.length > 0) cyRef.current.add(newNodes as cytoscape.ElementDefinition[]);
      if (newEdges.length > 0) cyRef.current.add(newEdges as cytoscape.ElementDefinition[]);
      cyRef.current.zoom(existingZoom);
      cyRef.current.pan(existingPan);
      setNodeCount(cyRef.current.nodes().length);
      setEdgeCount(cyRef.current.edges().length);
      setGraphEmpty(cyRef.current.nodes().length === 0);
    }
  }, [graphData, loadGraph]);

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
            <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-400 animate-spin rounded-full" />
            <span className="text-xs text-slate-500 font-mono">Loading graph…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="soc-panel px-6 py-4 max-w-sm text-center border-red-900/50">
            <AlertTriangle className="w-5 h-5 text-red-400 mx-auto mb-2" />
            <span className="text-red-400 text-xs font-mono">{error}</span>
          </div>
        </div>
      )}

      {/* Empty state — no mock data, just clear message */}
      {graphEmpty && !loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="text-center">
            <div className="text-xs text-slate-600 font-mono mb-2">No entities in graph</div>
            <div className="text-[10px] text-slate-700 font-mono">Run an investigation to populate the graph</div>
          </div>
        </div>
      )}

      {/* Live indicator */}
      {!loading && !error && !graphEmpty && (
        <div className="absolute top-3 right-3 z-20">
          <div className="soc-panel px-2.5 py-1 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[9px] text-slate-500 font-medium uppercase tracking-widest">Live</span>
          </div>
        </div>
      )}

      {/* Cytoscape container */}
      <div ref={containerRef} className="w-full h-full" />

      {/* ── Floating toolbar (bottom-right) ─────────────── */}
      <div className="absolute bottom-3 right-3 flex items-center gap-1 z-20">
        <button
          onClick={zoomIn}
          className="p-1.5 soc-panel hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-all"
          title="Zoom in"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={zoomOut}
          className="p-1.5 soc-panel hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-all"
          title="Zoom out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={fit}
          className="p-1.5 soc-panel hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-all"
          title="Fit to view"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-4 bg-slate-700 mx-0.5" />
        <button
          onClick={() => setLayoutType((l) => (l === "cose" ? "circle" : "cose"))}
          className={cn(
            "p-1.5 soc-panel hover:bg-slate-800 transition-all",
            layoutType === "cose" ? "text-cyan-500" : "text-slate-500"
          )}
          title={layoutType === "cose" ? "Switch to circle" : "Switch to force-directed"}
        >
          <Layers className="w-3.5 h-3.5" />
        </button>
        <label className="flex items-center gap-1 px-2 py-1.5 soc-panel cursor-pointer text-slate-500 hover:text-slate-300 transition-all">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          <span className="text-[10px] uppercase tracking-wider">Prune</span>
          <input
            type="checkbox"
            checked={pruneLeaves}
            onChange={(e) => onPruneChange(e.target.checked)}
            className="rounded-sm border-slate-700 bg-slate-900 text-amber-600 w-3 h-3"
          />
        </label>
      </div>

      {/* ── Stats badge (bottom-left) ──────────────────── */}
      {!graphEmpty && !loading && !error && (
        <div className="absolute bottom-3 left-3 z-20">
          <div className="soc-panel px-2.5 py-1 flex items-center gap-3">
            <span className="text-[10px] text-slate-500 font-mono">{nodeCount} nodes</span>
            <span className="w-px h-2.5 bg-slate-700" />
            <span className="text-[10px] text-slate-500 font-mono">{edgeCount} edges</span>
          </div>
        </div>
      )}
    </div>
  );
}
