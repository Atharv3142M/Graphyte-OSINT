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

function candidateApiBases(): string[] {
  const bases = new Set<string>();
  const envBase = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (envBase) bases.add(envBase);
  bases.add(API_BASE);

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    const host = window.location.hostname || "localhost";
    bases.add(`${protocol}//${host}:8000`);
    bases.add(`${protocol}//${host}:8001`);
    bases.add(`${protocol}//localhost:8000`);
    bases.add(`${protocol}//localhost:8001`);
    bases.add(`${protocol}//127.0.0.1:8000`);
    bases.add(`${protocol}//127.0.0.1:8001`);
  }
  return Array.from(bases);
}

async function fetchWithFallback(path: string, init?: RequestInit): Promise<Response> {
  const bases = candidateApiBases();
  let lastError: unknown = null;

  for (const base of bases) {
    try {
      const res = await fetch(`${base}${path}`, init);
      if (res.status === 404 && bases.length > 1) continue;
      return res;
    } catch (err) {
      lastError = err;
    }
  }
  throw new Error(
    `NetworkError when attempting to fetch resource. Checked API endpoints: ${bases.join(", ")}. ${String(lastError ?? "")}`.trim()
  );
}

function candidateWsBases(): string[] {
  return candidateApiBases().map((b) => b.replace(/^http/, "ws"));
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
  const res = await fetchWithFallback(`/api/agent/investigate`, {
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

/* ── Playbook dispatch ──────────────────────────────────── */

export interface PlaybookDispatchRequest {
  target: string;
  types: string[];
  intensity?: string;
}

export interface PlaybookDispatchResponse {
  playbook_id: string;
  modules: string[];
  module_labels: Record<string, string>;
  task_ids: string[];
  ws_url: string;
  target: string;
  types: string[];
}

export async function dispatchPlaybook(
  target: string,
  types: string[],
  intensity: string = "standard"
): Promise<PlaybookDispatchResponse> {
  const res = await fetchWithFallback(`/api/investigate`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ target, types, intensity }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail ?? `Request failed with ${res.status}`);
  }
  return res.json();
}

/* ── Playbook plan (from Redis) ─────────────────────────── */

/**
 * Fetch the initial module plan for a playbook.
 * Backend stores this at osint:playbook:{id}:plan as a Redis hash.
 */
export interface PlaybookModulePlan {
  module: string;
  label?: string;
  task_id: string;
  status: string;
  started_at: string | null;
}

export async function getPlaybookPlan(
  playbookId: string
): Promise<Record<string, PlaybookModulePlan>> {
  const res = await fetchWithFallback(`/api/playbook/${playbookId}/plan`, {
    headers: headers(),
  });
  if (!res.ok) {
    // Plan may not exist yet — return empty
    return {};
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
  raw_headers?: string;
  username?: string;
  usernames?: string[];
  query?: string;
  query_type?: string;
  max_depth?: number;
  max_pages?: number;
  max_concurrent?: number;
  timeout?: number;
  limit?: number;
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
  | "/api/deep-scraper"
  | "/api/ip-geolocation"
  | "/api/reverse-ip"
  | "/api/bgp-asn"
  | "/api/wayback"
  | "/api/email-header"
  | "/api/sherlock";

export async function runModule(
  endpoint: ModuleEndpoint,
  body: ModuleRequest
): Promise<ModuleResponse> {
  const res = await fetchWithFallback(`${endpoint}`, {
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
  const res = await fetchWithFallback(`/api/graph`, {
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
  const res = await fetchWithFallback(`/api/tasks/${taskId}`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Task status returned ${res.status}`);
  return res.json();
}

/* ── WebSocket stream helper ───────────────────────────── */

/**
 * Connects to the task stream WebSocket and calls onMessage for each
 * received line. Returns the WebSocket instance so the caller can close it.
 *
 * Falls back to HTTP polling on the result endpoint if the WebSocket
 * fails to connect within 3 seconds.
 */
export function createTaskStream(
  taskId: string,
  onMessage: (data: string, parsed: Record<string, unknown> | null) => void,
  onDone?: (finalResult?: unknown) => void,
  onError?: (err: string) => void,
  onStatusChange?: (status: "pending" | "started" | "success" | "failure") => void,
): WebSocket {
  const wsBases = candidateWsBases();
  let ws = new WebSocket(`${wsBases[0] || WS_BASE}/ws/task/${taskId}`);
  let wsIndex = 0;
  let wsConnected = false;
  let doneFired = false;
  let fallbackStarted = false;

  const bind = (socket: WebSocket) => {
    socket.onopen = () => {
      wsConnected = true;
      onStatusChange?.("started");
    };

    socket.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data as string) as Record<string, unknown>;
        onMessage(ev.data as string, parsed);

        if (parsed?.type === "done" && !doneFired) {
          doneFired = true;
          socket.close();
          const result = parsed?.data ?? parsed?.result ?? undefined;
          onDone?.(result);
        }

        if (parsed?.type === "result" && parsed?.status) {
          const status = String(parsed.status).toLowerCase();
          if (status === "success" || status === "failure" || status === "started" || status === "pending") {
            onStatusChange?.(status as "pending" | "started" | "success" | "failure");
          }
        }
      } catch {
        onMessage(ev.data as string, null);
      }
    };

    socket.onerror = () => {
      if (!wsConnected && wsIndex + 1 < wsBases.length) {
        wsIndex += 1;
        ws = new WebSocket(`${wsBases[wsIndex]}/ws/task/${taskId}`);
        bind(ws);
        return;
      }
      if (!wsConnected && !fallbackStarted) {
        fallbackStarted = true;
        pollTaskResult(taskId, onDone, onStatusChange);
      }
      onError?.("WebSocket connection error");
    };
    socket.onclose = () => {};
  };
  bind(ws);

  setTimeout(() => {
    if (!wsConnected && !fallbackStarted) {
      fallbackStarted = true;
      ws.close();
      pollTaskResult(taskId, onDone, onStatusChange);
    }
  }, 3000);

  return ws;
}

function pollTaskResult(
  taskId: string,
  onDone?: (result?: unknown) => void,
  onStatusChange?: (status: "pending" | "started" | "success" | "failure") => void,
): void {
  let attempts = 0;
  const MAX_ATTEMPTS = 150;
  const INTERVAL_MS = 2000;

  const poll = async () => {
    if (attempts >= MAX_ATTEMPTS) {
      onStatusChange?.("failure");
      return;
    }
    attempts++;

    try {
      const taskStatus = await getTaskStatus(taskId);
      const normalized = String(taskStatus.status).toLowerCase();
      if (normalized === "success" || normalized === "failure" || normalized === "started" || normalized === "pending") {
        onStatusChange?.(normalized as "pending" | "started" | "success" | "failure");
      }

      if (normalized === "success" || normalized === "failure") {
        onDone?.(taskStatus.result);
        return;
      }

      setTimeout(poll, INTERVAL_MS);
    } catch {
      setTimeout(poll, INTERVAL_MS);
    }
  };

  poll();
}

/* ── Playbook WebSocket stream ─────────────────────────── */

/**
 * Payload shape from /ws/playbook/{id}:
 *   { type: "result", module: string, data: {...} }
 *   { type: "done",   module: string, status: "success"|"failure", error?: string }
 */
export interface PlaybookWSMessage {
  type: "result" | "done" | "stdout" | "stderr";
  module: string;
  data?: Record<string, unknown>;
  status?: string;
  error?: string;
}

/**
 * Connects to the shared playbook WebSocket at /ws/playbook/{playbook_id}.
 * All module results for the investigation fan out through this single channel.
 *
 * onModuleResult(module, data) — called per incoming result
 * onModuleDone(module, status, error) — called when a module completes (type=done)
 * onAllDone() — called when all modules have sent "done"
 *
 * Returns the WebSocket so the caller can close it.
 */
export function createPlaybookStream(
  playbookId: string,
  onModuleResult: (module: string, data: Record<string, unknown>) => void,
  onModuleDone: (module: string, status: string, error?: string) => void,
  onAllDone?: () => void,
  onError?: (err: string) => void,
  expectedModules?: string[],
  onStreamLog?: (module: string, text: string) => void,
): WebSocket {
  const wsBases = candidateWsBases();
  let ws = new WebSocket(`${wsBases[0] || WS_BASE}/ws/playbook/${playbookId}`);
  let wsIndex = 0;
  let wsConnected = false;
  const doneModules = new Set<string>();
  const expected = new Set((expectedModules ?? []).map((m) => (m.startsWith("tasks.") ? m : `tasks.${m}`)));
  const canonical = (m: string) => (m.startsWith("tasks.") ? m : `tasks.${m}`);

  const bind = (socket: WebSocket) => {
    socket.onopen = () => {
      wsConnected = true;
    };
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as PlaybookWSMessage;
        const moduleName = canonical(msg.module ?? "");

        if (msg.type === "result" && msg.data) {
          onModuleResult(moduleName, msg.data);
        } else if (msg.type === "stdout" || msg.type === "stderr") {
          if (msg.data && typeof msg.data === "string") {
            onStreamLog?.(moduleName, msg.data);
          } else {
             // Fallback if data is a dict somehow, though backend sends text string data for stdout/stderr
            onStreamLog?.(moduleName, String(msg.data));
          }
        } else if (msg.type === "done") {
          doneModules.add(moduleName);
          onModuleDone(moduleName, msg.status ?? "success", msg.error);
          if (expected.size > 0 && doneModules.size >= expected.size) {
            onAllDone?.();
          }
          if (msg.error) {
            onError?.(`module ${moduleName} error: ${msg.error}`);
          }
        }
      } catch {
        // Ignore parse errors
      }
    };
    socket.onerror = () => {
      if (!wsConnected && wsIndex + 1 < wsBases.length) {
        wsIndex += 1;
        ws = new WebSocket(`${wsBases[wsIndex]}/ws/playbook/${playbookId}`);
        bind(ws);
        return;
      }
      onError?.("Playbook WebSocket error");
    };
    socket.onclose = () => {
      if (expected.size === 0 || doneModules.size >= expected.size) {
        onAllDone?.();
      }
    };
  };
  bind(ws);

  return ws;
}
