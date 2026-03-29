"use client";

import { useCallback } from "react";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { useInvestigationStore } from "@/store/useInvestigationStore";
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
      <div className="absolute top-3 left-3 z-20">
        <div className="soc-panel px-3 py-1.5 flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">Graph Workspace</span>
          </div>
          <div className="w-px h-3 bg-slate-700" />
          <span className="text-[9px] text-slate-600">Click nodes to inspect</span>
        </div>
      </div>
    </div>
  );
}
