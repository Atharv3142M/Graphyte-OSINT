"use client";

import { useCallback } from "react";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { useInvestigationStore } from "@/store/useInvestigationStore";
import { ZoomIn, ZoomOut, Maximize2, Layers, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function WorkspacePage() {
  const selectedNode = useInvestigationStore((s) => s.selectedNode);
  const detailPanelOpen = useInvestigationStore((s) => s.detailPanelOpen);
  const pruneLeaves = useInvestigationStore((s) => s.pruneLeaves);
  const setSelectedNode = useInvestigationStore((s) => s.setSelectedNode);
  const closeDetailPanel = useInvestigationStore((s) => s.closeDetailPanel);
  const setPruneLeaves = useInvestigationStore((s) => s.setPruneLeaves);

  const handleNodeSelect = useCallback(
    (node: import("@/components/NodeDetailPanel").NodeDetail | null) => {
      if (node) {
        setSelectedNode(node);
      } else {
        closeDetailPanel();
      }
    },
    [setSelectedNode, closeDetailPanel]
  );

  return (
    <div className="h-full overflow-hidden bg-slate-950 relative">
      {/* Graph Canvas - Full Screen */}
      <GraphCanvas
        pruneLeaves={pruneLeaves}
        onPruneChange={setPruneLeaves}
        onNodeSelect={handleNodeSelect}
        selectedNodeId={selectedNode?.id ?? null}
        className="w-full h-full"
      />

      {/* Node Detail Panel */}
      <NodeDetailPanel
        node={selectedNode}
        onClose={closeDetailPanel}
        isOpen={detailPanelOpen}
      />

      {/* Workspace Info Badge */}
      <div className="absolute top-4 left-4 z-20">
        <div className="glass-panel rounded-xl px-4 py-2 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-slate-300 font-medium">Graph Workspace</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="text-xs text-slate-500">
            Click nodes to inspect, drag to explore
          </div>
        </div>
      </div>
    </div>
  );
}
