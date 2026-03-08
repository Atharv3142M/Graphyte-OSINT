"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import cytoscape, { Core } from "cytoscape";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StixGraphProps {
  className?: string;
  pruneLeaves?: boolean;
}

/**
 * Cytoscape.js graph for STIX data. Uses canvas renderer (GPU-accelerated via browser compositing).
 * Supports leaf-node pruning for large graphs (10k+ nodes).
 */
export function StixGraph({ className = "", pruneLeaves = false }: StixGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const loadGraph = async () => {
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
                width: 20,
                height: 20,
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
            name: nodes.length > 500 ? "cose" : "cose",
            animate: nodes.length < 500,
            animationDuration: 300,
          },
          minZoom: 0.1,
          maxZoom: 4,
          wheelSensitivity: 0.3,
        });
        cyRef.current = cy;
        setNodeCount(cy.nodes().length);
        setEdgeCount(cy.edges().length);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [pruneLeaves]);

  return (
    <div className={`relative rounded-xl border border-slate-700 overflow-hidden bg-slate-900 ${className}`}>
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
      <div
        ref={containerRef}
        className="w-full h-full min-h-[360px]"
        style={{ height: 420 }}
      />
      <div className="absolute bottom-2 left-2 text-xs text-slate-500">
        {nodeCount} nodes · {edgeCount} edges
      </div>
    </div>
  );
}
