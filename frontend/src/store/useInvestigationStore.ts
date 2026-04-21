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

/* ── Per-module result entry ─────────────────────────────── */

export type ResultStatus = "pending" | "running" | "done" | "error";

export interface ModuleResultEntry {
  taskId: string;
  label?: string;
  status: ResultStatus;
  result: Record<string, unknown> | null;
  timestamp: number;
  error?: string;
}

/* ── Playbook result store ──────────────────────────────── */
/*
 * resultStore is keyed by playbook_id.
 * Each value is a PlaybookResults object containing a map of
 * module_name -> ModuleResultEntry.
 *
 * This matches the Redis plan structure:
 *   playbook_id -> { modules: { module_name -> { taskId, status, result, timestamp } } }
 */

export interface PlaybookResults {
  target: string;
  types: string[];
  modules: Record<string, ModuleResultEntry>;
  startedAt: number;
}

export interface ResultStore {
  [playbookId: string]: PlaybookResults;
}

/* ── Store shape ───────────────────────────────────────── */

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

  /* Module results — keyed by playbook_id */
  resultStore: ResultStore;

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

  /* Playbook result store actions */
  initPlaybook: (
    playbookId: string,
    target: string,
    types: string[],
    plan: Record<string, { module: string; task_id: string; status: string; label?: string }>
  ) => void;
  setModuleStatus: (playbookId: string, module: string, status: ResultStatus, error?: string) => void;
  setModuleResult: (playbookId: string, module: string, data: Record<string, unknown>) => void;
  clearPlaybook: (playbookId: string) => void;
  clearAllResults: () => void;

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
  resultStore: {} as ResultStore,
  selectedNode: null,
  detailPanelOpen: false,
  pruneLeaves: false,
};

/* ── Store ─────────────────────────────────────────────── */

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

  /* ── Playbook result store actions ────────────────────── */

  initPlaybook: (playbookId, target, types, plan) =>
    set((state) => {
      // plan is keyed by display name; value has task_id + module (task name)
      const modules: Record<string, ModuleResultEntry> = {};
      for (const [_modKey, entry] of Object.entries(plan)) {
        const modName = entry.module ?? _modKey;
        modules[modName] = {
          taskId: entry.task_id,
          label: entry.label ?? modName,
          status: (entry.status as ResultStatus) ?? "pending",
          result: null,
          timestamp: Date.now(),
        };
      }
      return {
        resultStore: {
          ...state.resultStore,
          [playbookId]: { target, types, modules, startedAt: Date.now() },
        },
      };
    }),

  setModuleStatus: (playbookId, module, status, error) =>
    set((state) => {
      const pb = state.resultStore[playbookId];
      if (!pb) return state;
      const mod = pb.modules[module];
      if (!mod) return state;
      return {
        resultStore: {
          ...state.resultStore,
          [playbookId]: {
            ...pb,
            modules: {
              ...pb.modules,
              [module]: {
                ...mod,
                status,
                ...(error ? { error } : {}),
              },
            },
          },
        },
      };
    }),

  setModuleResult: (playbookId, module, data) =>
    set((state) => {
      const pb = state.resultStore[playbookId];
      if (!pb) return state;
      const mod = pb.modules[module];
      if (!mod) return state;
      return {
        resultStore: {
          ...state.resultStore,
          [playbookId]: {
            ...pb,
            modules: {
              ...pb.modules,
              [module]: {
                ...mod,
                result: data,
                status: "done" as ResultStatus,
                timestamp: Date.now(),
              },
            },
          },
        },
      };
    }),

  clearPlaybook: (playbookId) =>
    set((state) => {
      const next = { ...state.resultStore };
      delete next[playbookId];
      return { resultStore: next };
    }),

  clearAllResults: () => set({ resultStore: {} as ResultStore }),

  reset: () => set(initialState),
}));
