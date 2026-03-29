/**
 * Centralized API client for the OSINT Platform.
 * All HTTP requests to the backend go through here.
 */

import type { GraphData } from "@/store/useInvestigationStore";

/* ── Environment ───────────────────────────────────────── */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export const DEFAULT_TENANT_ID =
  process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ||
  "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

/* ── Tenant header (used on every request) ─────────────── */

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Tenant-ID": DEFAULT_TENANT_ID,
  };
}

/* ── Investigation ──────────────────────────────────────── */

export interface InvestigateRequest {
  goal: string;
  thread_id?: string;
}

export interface InvestigateResponse {
  success: boolean;
  thread_id: string;
  summary?: string;
  threat_score: number;
  stix_bundle?: unknown;
  investigation_context?: unknown[];
}

export async function investigate(
  goal: string,
  threadId?: string
): Promise<InvestigateResponse> {
  const res = await fetch(`${API_BASE}/api/agent/investigate`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ goal, thread_id: threadId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail ?? `Request failed with ${res.status}`);
  }
  return res.json();
}

/* ── Standalone module endpoints ─────────────────────────── */

export interface ModuleRequest {
  target?: string;
  host?: string;
  domain?: string;
  url?: string;
  file_path?: string;
  ports?: number[];
  brute_subdomains?: boolean;
  brute_force?: boolean;
}

export interface ModuleResponse {
  task_id: string;
  status: string;
  stream_url: string;
  result_url: string;
}

export type ModuleEndpoint =
  | "/api/shodan"
  | "/api/censys"
  | "/api/port-scan"
  | "/api/dns-intel"
  | "/api/whois"
  | "/api/ssl-analyze"
  | "/api/http-security"
  | "/api/tech-stack"
  | "/api/metadata-extract"
  | "/api/cyberninja"
  | "/api/xrecon"
  | "/api/social-hunter"
  | "/api/cert-transparency"
  | "/api/deep-scraper";

export async function runModule(
  endpoint: ModuleEndpoint,
  body: ModuleRequest
): Promise<ModuleResponse> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail ?? `Request failed with ${res.status}`);
  }
  return res.json();
}

/* ── Graph ─────────────────────────────────────────────── */

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/api/graph`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Graph endpoint returned ${res.status}`);
  }
  const data = await res.json();
  return {
    nodes: data.elements?.nodes ?? [],
    edges: data.elements?.edges ?? [],
  };
}

/* ── Task status ───────────────────────────────────────── */

export interface TaskStatus {
  task_id: string;
  status: string;
  result?: unknown;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Task status returned ${res.status}`);
  return res.json();
}

/* ── WebSocket stream helper ───────────────────────────── */

/**
 * Connects to the task stream WebSocket and calls onMessage for each
 * received line. Returns the WebSocket instance so the caller can close it.
 */
export function createTaskStream(
  taskId: string,
  onMessage: (data: string, parsed: Record<string, unknown> | null) => void,
  onDone?: () => void,
  onError?: (err: string) => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/task/${taskId}`);

  ws.onmessage = (ev) => {
    try {
      const parsed = JSON.parse(ev.data as string) as Record<string, unknown>;
      onMessage(ev.data as string, parsed);
      if (parsed?.type === "done") {
        ws.close();
        onDone?.();
      }
    } catch {
      // Plain text — pass raw string
      onMessage(ev.data as string, null);
    }
  };

  ws.onerror = () => {
    onError?.("WebSocket connection error");
  };

  ws.onclose = () => {
    onDone?.();
  };

  return ws;
}
