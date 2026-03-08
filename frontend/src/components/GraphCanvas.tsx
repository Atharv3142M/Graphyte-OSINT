"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import cytoscape, { Core, NodeSingular } from "cytoscape";
import { ZoomIn, ZoomOut, Network, Layers, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NodeDetail } from "./NodeDetailPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
      cyRef.current.layout({ name: layoutType, animate: true, animationDuration: 300 }).run();
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
        const nodeIds = new Set(nodes.map((n: { data: { id: string } }) => n.data.id));
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
      const cy = cytoscape({
        container: containerRef.current,
        elements: { nodes, edges },
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#06b6d4",
              label: "data(label)",
              "text-valign": "bottom",
              "text-halign": "center",
              "font-size": "10px",
              width: 24,
              height: 24,
            },
          },
          {
            selector: "node.ipv4_addr",
            style: { "background-color": "#22c55e" },
          },
          {
            selector: "node.domain_name",
            style: { "background-color": "#8b5cf6" },
          },
          {
            selector: "node.network_traffic",
            style: { "background-color": "#f59e0b" },
          },
          {
            selector: "node.note",
            style: { "background-color": "#ec4899" },
          },
          {
            selector: "node.server",
            style: { "background-color": "#ef4444", "border-width": 2, "border-color": "#fca5a5" },
          },
          {
            selector: "node:selected",
            style: { "border-width": 3, "border-color": "#06b6d4" },
          },
          {
            selector: "edge",
            style: {
              "line-color": "#64748b",
              "target-arrow-color": "#64748b",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
            },
          },
        ],
        layout: {
          name: "cose",
          animate: nodes.length < 500,
          animationDuration: 300,
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
    <div className={cn("relative rounded-xl border border-slate-700 overflow-hidden bg-slate-900", className)}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
          <span className="text-slate-400">Loading graph…</span>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
          <span className="text-red-400 text-sm">{error}</span>
        </div>
      )}

      <div ref={containerRef} className="w-full h-full min-h-[400px]" style={{ height: 480 }} />

      {/* Floating toolbar */}
      <div className="absolute top-3 left-3 flex flex-col gap-2">
        <button
          onClick={zoomIn}
          className="p-2 rounded-lg bg-slate-800/90 border border-slate-600 hover:bg-slate-700 text-slate-300 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          className="p-2 rounded-lg bg-slate-800/90 border border-slate-600 hover:bg-slate-700 text-slate-300 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={fit}
          className="p-2 rounded-lg bg-slate-800/90 border border-slate-600 hover:bg-slate-700 text-slate-300 transition-colors"
          title="Fit to view"
        >
          <Network className="w-4 h-4" />
        </button>
      </div>

      <div className="absolute top-3 right-3 flex flex-col gap-2 items-end">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/90 border border-slate-600">
          <span className="text-xs text-slate-400">Force-directed</span>
          <button
            onClick={() => setLayoutType((l) => (l === "cose" ? "circle" : "cose"))}
            className={cn(
              "w-9 h-4 rounded-full relative transition-colors",
              layoutType === "cose" ? "bg-cyan-600" : "bg-slate-600"
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
                layoutType === "cose" ? "left-1" : "left-5"
              )}
            />
          </button>
        </div>
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/90 border border-slate-600 cursor-pointer">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <span className="text-xs text-slate-400">Prune leaf nodes</span>
          <input
            type="checkbox"
            checked={pruneLeaves}
            onChange={(e) => onPruneChange(e.target.checked)}
            className="rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-cyan-500"
          />
        </label>
      </div>

      <div className="absolute bottom-2 left-2 flex items-center gap-2">
        <span className="text-xs text-slate-500">{nodeCount} nodes · {edgeCount} edges</span>
        <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400">Vuln badges on servers</span>
      </div>
    </div>
  );
}
