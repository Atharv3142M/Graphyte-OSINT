/**
 * Global investigation state — powered by Zustand.
 * Tracks the active task, WebSocket connection, graph data, and selected node.
 */

import { create } from "zustand";
import type { NodeDetail } from "@/components/NodeDetailPanel";

/* ── Types ─────────────────────────────────────────────── */

export type InvestigationStatus =
  | "idle"
  | "queued"
  | "running"
  | "done"
  | "error";

export interface GraphData {
  nodes: OSINTNode[];
  edges: OSINTEdge[];
}

export interface OSINTNode {
  data: OSINTNodeData;
}

export interface OSINTNodeData {
  id: string;
  label?: string;
  type?: string;
  riskScore?: number;
  stix?: Record<string, unknown>;
  entityResolution?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface OSINTEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type?: string;
    label?: string;
    [key: string]: unknown;
  };
}

/* ── Store shape ────────────────────────────────────────── */

interface InvestigationStore {
  /* Active investigation */
  currentTaskId: string | null;
  investigationStatus: InvestigationStatus;
  threadId: string | null;
  threatScore: number | null;
  orchestratorSummary: string | null;

  /* Live terminal stream */
  streamLog: string[];

  /* STIX graph */
  graphData: GraphData | null;

  /* Selected node for detail panel */
  selectedNode: NodeDetail | null;
  detailPanelOpen: boolean;
  pruneLeaves: boolean;

  /* Actions */
  setTaskId: (taskId: string | null) => void;
  setStatus: (status: InvestigationStatus) => void;
  setThreadId: (threadId: string | null) => void;
  setThreatScore: (score: number | null) => void;
  setOrchestratorSummary: (summary: string | null) => void;
  appendLog: (line: string) => void;
  clearLog: () => void;
  setGraphData: (data: GraphData | null) => void;
  setSelectedNode: (node: NodeDetail | null) => void;
  openDetailPanel: (node: NodeDetail) => void;
  closeDetailPanel: () => void;
  setPruneLeaves: (v: boolean) => void;
  reset: () => void;
}

/* ── Initial state ──────────────────────────────────────── */

const initialState = {
  currentTaskId: null,
  investigationStatus: "idle" as InvestigationStatus,
  threadId: null,
  threatScore: null,
  orchestratorSummary: null,
  streamLog: [],
  graphData: null,
  selectedNode: null,
  detailPanelOpen: false,
  pruneLeaves: false,
};

/* ── Store ──────────────────────────────────────────────── */

export const useInvestigationStore = create<InvestigationStore>((set) => ({
  ...initialState,

  setTaskId: (taskId) => set({ currentTaskId: taskId }),

  setStatus: (status) => set({ investigationStatus: status }),

  setThreadId: (threadId) => set({ threadId }),

  setThreatScore: (score) => set({ threatScore: score }),

  setOrchestratorSummary: (summary) => set({ orchestratorSummary: summary }),

  appendLog: (line) =>
    set((state) => ({ streamLog: [...state.streamLog, line].slice(-500) })),

  clearLog: () => set({ streamLog: [] }),

  setGraphData: (data) => set({ graphData: data }),

  setSelectedNode: (node) => set({ selectedNode: node }),

  openDetailPanel: (node) => set({ selectedNode: node, detailPanelOpen: true }),

  closeDetailPanel: () => set({ selectedNode: null, detailPanelOpen: false }),

  setPruneLeaves: (v) => set({ pruneLeaves: v }),

  reset: () => set(initialState),
}));
