"use client";

import { useCallback, useState } from "react";
import { LayoutList, Focus, Filter, Wrench } from "lucide-react";
import { GraphCanvas } from "@/components/GraphCanvas";
import { GlobalTerminal } from "@/components/layout/GlobalTerminal";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { ResultPanel } from "@/components/ResultPanel";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export default function WorkspacePage() {
  const [resultPanelOpen, setResultPanelOpen] = useState(true);
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
    <div className="h-full overflow-hidden bg-slate-950 relative flex flex-col">
      {/* Toolbar */}
      <div className="absolute top-4 left-4 z-20 rounded-xl border border-slate-800 bg-slate-900/95 px-3 py-2.5 flex items-center gap-3">
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-[10px] uppercase tracking-widest text-amber-300 font-mono">
          <Wrench className="w-3 h-3" />
          Advanced
        </span>
        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">Investigation Workspace</p>
        <button
          className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-cyan-300"
          onClick={() => setPruneLeaves(!pruneLeaves)}
        >
          <Filter className="w-3.5 h-3.5" />
          {pruneLeaves ? "Prune On" : "Prune Off"}
        </button>
        <button
          className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-cyan-300"
          onClick={() => setResultPanelOpen((v) => !v)}
        >
          <LayoutList className="w-3.5 h-3.5" />
          {resultPanelOpen ? "Hide Results" : "Show Results"}
        </button>
        <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
          <Focus className="w-3 h-3" /> Graph focus mode
        </span>
      </div>

      {/* Graph fills the area above the terminal */}
      <div className="flex-1 relative">
        <GraphCanvas
          pruneLeaves={pruneLeaves}
          onPruneChange={setPruneLeaves}
          onNodeSelect={handleNodeSelect}
          selectedNodeId={selectedNode?.id ?? null}
          className="w-full h-full"
        />
      </div>

      {/* Terminal lives only on the Advanced Workspace, not the beginner dashboard */}
      <div className="flex-shrink-0">
        <GlobalTerminal />
      </div>

      <NodeDetailPanel
        node={selectedNode}
        onClose={closeDetailPanel}
        isOpen={detailPanelOpen}
      />
      <ResultPanel isOpen={resultPanelOpen} onClose={() => setResultPanelOpen(false)} />
    </div>
  );
}
