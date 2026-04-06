"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  Search,
  Target,
  Shield,
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Database,
  Globe,
  Lock,
  RefreshCw,
  Server,
  Wifi,
  LayoutList,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  investigate,
  dispatchPlaybook,
  createPlaybookStream,
  fetchGraph,
} from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";
import { classify, normalizeInput, type DetectedType } from "@/lib/classifier";
import { ResultPanel } from "@/components/ResultPanel";

type WorkflowIntensity = "low" | "standard" | "aggressive" | "agent";

const INTENSITIES: { value: WorkflowIntensity; label: string; color: string }[] = [
  { value: "low", label: "Passive", color: "text-emerald-400" },
  { value: "standard", label: "Standard", color: "text-cyan-400" },
  { value: "aggressive", label: "Aggressive", color: "text-amber-400" },
  { value: "agent", label: "AI Agent", color: "text-violet-400" },
];

export default function DashboardPage() {
  const [target, setTarget] = useState("");
  const [intensity, setIntensity] = useState<WorkflowIntensity>("standard");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [resultPanelOpen, setResultPanelOpen] = useState(false);

  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0 });
  const [recentTasks, setRecentTasks] = useState<Array<{
    id: string;
    target: string;
    type: string;
    status: "completed" | "running" | "failed";
    timestamp: string;
    riskScore?: number;
  }>>([]);

  // Active playbook WebSocket ref — closed on next run or unmount
  const wsRef = useRef<WebSocket | null>(null);

  const appendLog = useInvestigationStore((s) => s.appendLog);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);
  const setStatus = useInvestigationStore((s) => s.setStatus);
  const initPlaybook = useInvestigationStore((s) => s.initPlaybook);
  const setModuleStatus = useInvestigationStore((s) => s.setModuleStatus);
  const setModuleResult = useInvestigationStore((s) => s.setModuleResult);
  const resultStore = useInvestigationStore((s) => s.resultStore);

  // Fetch real graph stats on mount
  useEffect(() => {
    const loadGraphStats = async () => {
      try {
        const data = await fetchGraph();
        const nodeCount = data.nodes?.length ?? 0;
        const edgeCount = data.edges?.length ?? 0;
        setGraphStats({ nodes: nodeCount, edges: edgeCount });
        if (nodeCount > 0) {
          setGraphData(data);
        }
      } catch {
        // Graph may be empty — no data to load
      }
    };
    loadGraphStats();
  }, [setGraphData]);

  // Poll graph stats whenever a task completes
  const refreshStats = useCallback(async () => {
    try {
      const data = await fetchGraph();
      setGraphStats({ nodes: data.nodes?.length ?? 0, edges: data.edges?.length ?? 0 });
      setGraphData(data);
    } catch {
      // Non-blocking
    }
  }, [setGraphData]);

  const handleInvestigate = useCallback(async () => {
    if (!target.trim()) return;
    setIsRunning(true);
    setStatus("running");
    appendLog(`\x1b[35m[Dashboard]\x1b[0m Starting investigation: "${target}"`);

    const taskEntry = {
      id: Date.now().toString(),
      target: target.trim(),
      type: "Playbook",
      status: "running" as const,
      timestamp: "Just now",
    };
    setRecentTasks((prev) => [taskEntry, ...prev.slice(0, 9)]);

    try {
      if (intensity === "agent") {
        const res = await investigate(`Investigate ${target}`);
        appendLog(`\x1b[32m[Agent]\x1b[0m Thread ${res.thread_id} — threat_score: ${res.threat_score}`);
        if (res.stix_bundle) {
          const bundle = res.stix_bundle as { objects?: Array<{ id: string; type: string; name?: string }> };
          if (bundle.objects) {
            const nodes = bundle.objects.map((obj) => ({
              data: { id: obj.id, type: obj.type, label: obj.name ?? obj.id },
            }));
            setGraphData({ nodes, edges: [] });
          }
        }
        setStatus("done");
        setRecentTasks((prev) =>
          prev.map((t) => t.id === taskEntry.id ? { ...t, status: "completed" as const } : t)
        );
        await refreshStats();
      } else {
        // ── Phase 2: Smart search via playbook dispatch ──────────────────
        const normalized = normalizeInput(target.trim());
        const detectedTypes = classify(normalized);
        const typesToSend: string[] = detectedTypes.length > 0
          ? detectedTypes
          : (["domain"] as DetectedType[]);

        // Normalise intensity to what the backend expects
        // @ts-ignore — agent is handled in the earlier branch, this cast is intentional
        const intensityValue = (intensity === "agent" ? "standard" : intensity) as "low" | "standard" | "aggressive";

        appendLog(`\x1b[36m[Playbook]\x1b[0m Dispatching to /api/investigate — target: ${normalized}, types: ${typesToSend.join(", ")}, intensity: ${intensityValue}`);

        let dispatchRes: Awaited<ReturnType<typeof dispatchPlaybook>> | null = null;
        try {
          dispatchRes = await dispatchPlaybook(normalized, typesToSend, intensityValue);
        } catch (err) {
          appendLog(`\x1b[31m[Error]\x1b[0m ${err instanceof Error ? err.message : String(err)}`);
          setStatus("error");
          setIsRunning(false);
          return;
        }

        const { playbook_id, modules, ws_url } = dispatchRes as { playbook_id: string; modules: string[]; ws_url: string };
        appendLog(`\x1b[36m[Playbook]\x1b[0m playbook_id=${playbook_id}, modules=${modules.join(", ")}`);
        appendLog(`\x1b[90mWS: ${ws_url}\x1b[0m`);

        // Close any previous playbook WS
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }

        // Track this playbook in the store
        // We initialise with the module list from the dispatch response.
        // Since the plan endpoint may not have written to Redis yet,
        // we initialise from the response payload directly.
        const fakePlan: Record<string, { module: string; task_id: string; status: string }> = {};
        modules.forEach((m, i) => {
          fakePlan[m] = { module: m, task_id: "", status: "queued" };
        });
        initPlaybook(playbook_id, normalized, typesToSend, fakePlan);

        // Open playbook WebSocket — this is the single channel all module results flow through
        const ws = createPlaybookStream(
          playbook_id,
          // onModuleResult: store each result as it streams in
          (module, data) => {
            appendLog(`\x1b[32m[${module}]\x1b[0m result received`);
            setModuleResult(playbook_id, module, data);
            if (data?.error) {
              appendLog(`\x1b[31m[Error]\x1b[0m ${data.error}`);
            }
          },
          // onModuleDone: mark the module done or errored
          (module, _status, error) => {
            if (error) {
              appendLog(`\x1b[31m[${module}]\x1b[0m ${error}`);
              setModuleStatus(playbook_id, module, "error", error);
            } else {
              appendLog(`\x1b[32m[${module}]\x1b[0m done`);
              setModuleStatus(playbook_id, module, "done");
            }
          },
          // onAllDone: investigation complete
          () => {
            appendLog(`\x1b[32m[Playbook]\x1b[0m All modules complete`);
            setIsRunning(false);
            setStatus("done");
            setRecentTasks((prev) =>
              prev.map((t) => t.id === taskEntry.id ? { ...t, status: "completed" as const } : t)
            );
            refreshStats().catch(console.error);
          },
          // onError
          (err) => {
            appendLog(`\x1b[31m[WS Error]\x1b[0m ${err}`);
          },
        );

        wsRef.current = ws;
        appendLog(`\x1b[32m[WS]\x1b[0m Connected to /ws/playbook/${playbook_id}`);
        setResultPanelOpen(true);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog(`\x1b[31m[Error]\x1b[0m ${msg}`);
      setStatus("error");
      setRecentTasks((prev) =>
        prev.map((t) => t.id === taskEntry.id ? { ...t, status: "failed" as const } : t)
      );
    } finally {
      setIsRunning(false);
    }
  }, [target, intensity, appendLog, setGraphData, setStatus, refreshStats, initPlaybook, setModuleStatus, setModuleResult]);

  const currentIntensity = INTENSITIES.find((i) => i.value === intensity)!;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case "running": return <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />;
      case "failed": return <AlertTriangle className="w-4 h-4 text-red-400" />;
      default: return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getRiskColor = (score?: number) => {
    if (score === undefined) return "text-slate-400";
    if (score >= 0.7) return "text-red-400";
    if (score >= 0.4) return "text-amber-400";
    return "text-emerald-400";
  };

  // Calculate risk distribution from recent tasks
  const completedTasks = recentTasks.filter((t) => t.status === "completed");
  const criticalCount = completedTasks.filter((t) => (t.riskScore ?? 0) >= 0.7).length;
  const highCount = completedTasks.filter((t) => (t.riskScore ?? 0) >= 0.4 && (t.riskScore ?? 0) < 0.7).length;
  const mediumCount = completedTasks.filter((t) => (t.riskScore ?? 0) >= 0.2 && (t.riskScore ?? 0) < 0.4).length;
  const lowCount = completedTasks.filter((t) => (t.riskScore ?? 0) < 0.2).length;
  const totalScans = graphStats.nodes;
  const securityScore = totalScans > 0
    ? Math.min(99, 40 + Math.round((graphStats.edges / Math.max(graphStats.nodes, 1)) * 20))
    : 0;

  // Total running modules across all playbooks (for badge count)
  const totalRunningModules = Object.values(resultStore).reduce((sum, pb) => {
    return sum + Object.values(pb.modules).filter((m) => m.status === "pending" || m.status === "running").length;
  }, 0);

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-4 max-w-7xl mx-auto space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">OSINT Command Center</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {graphStats.nodes > 0
                ? `${graphStats.nodes} entities, ${graphStats.edges} relationships in graph`
                : "No entities in graph — run an investigation"}
            </p>
          </div>
          <button
            onClick={() => refreshStats()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-cyan-400 border border-slate-800 hover:border-slate-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>

        {/* Quick Investigation */}
        <div className="border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-3.5 h-3.5 text-cyan-400" />
            <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Quick Investigation</h2>
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleInvestigate()}
                placeholder="IP, domain, URL, email, or username..."
                disabled={isRunning}
                className="w-full pl-8 pr-3 py-2 text-xs border border-slate-700 bg-slate-950 text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-600 transition-colors font-mono"
              />
            </div>
            {/* Intensity selector */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen((v) => !v)}
                className="flex items-center gap-1.5 px-2.5 py-2 text-xs font-medium border border-slate-700 hover:border-slate-600 transition-colors text-slate-300"
              >
                <span className={currentIntensity.color}>{currentIntensity.label}</span>
                <ChevronDown className="w-3 h-3 text-slate-500" />
              </button>
              {dropdownOpen && (
                <div className="absolute top-full right-0 mt-1 border border-slate-700 bg-slate-900 py-1 min-w-[110px] z-50">
                  {INTENSITIES.map((i) => (
                    <button
                      key={i.value}
                      onClick={() => { setIntensity(i.value); setDropdownOpen(false); }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs font-medium hover:bg-slate-800 transition-colors",
                        i.color,
                        intensity === i.value && "bg-slate-800"
                      )}
                    >
                      {i.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={() => setResultPanelOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-2 text-xs border border-slate-700 hover:border-slate-600 transition-colors text-slate-400"
              title="View results"
            >
              <LayoutList className="w-3.5 h-3.5" />
              <span>Results</span>
              {totalRunningModules > 0 && (
                <span className="text-cyan-400 font-mono">{totalRunningModules}</span>
              )}
            </button>
            <button
              onClick={handleInvestigate}
              disabled={isRunning || !target.trim()}
              className={cn(
                "px-4 py-2 text-xs font-semibold transition-all border",
                isRunning
                  ? "border-slate-700 text-slate-600 bg-slate-900 cursor-wait"
                  : "border-cyan-800 text-cyan-400 hover:bg-cyan-950 hover:border-cyan-700"
              )}
            >
              {isRunning ? "Running..." : "Investigate"}
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          <div className="border border-slate-800 bg-slate-900/60 p-3">
            <div className="flex items-center justify-between mb-2">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Nodes</span>
            </div>
            <div className="text-xl font-bold text-slate-100 font-mono">{graphStats.nodes}</div>
            <div className="text-[10px] text-slate-600 mt-0.5">entities in graph</div>
          </div>
          <div className="border border-slate-800 bg-slate-900/60 p-3">
            <div className="flex items-center justify-between mb-2">
              <Globe className="w-3.5 h-3.5 text-violet-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Edges</span>
            </div>
            <div className="text-xl font-bold text-slate-100 font-mono">{graphStats.edges}</div>
            <div className="text-[10px] text-slate-600 mt-0.5">relationships</div>
          </div>
          <div className="border border-slate-800 bg-slate-900/60 p-3">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Scans</span>
            </div>
            <div className="text-xl font-bold text-slate-100 font-mono">{graphStats.nodes}</div>
            <div className="text-[10px] text-slate-600 mt-0.5">total entities</div>
          </div>
          <div className="border border-slate-800 bg-slate-900/60 p-3">
            <div className="flex items-center justify-between mb-2">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Score</span>
            </div>
            <div className="text-xl font-bold text-slate-100 font-mono">{securityScore}</div>
            <div className="text-[10px] text-slate-600 mt-0.5">security posture</div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Recent Tasks</h2>
            </div>
            {recentTasks.length > 0 && (
              <button
                onClick={() => setRecentTasks([])}
                className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          {recentTasks.length === 0 ? (
            <div className="text-xs text-slate-600 py-4 text-center font-mono">
              No recent tasks — run an investigation to populate this list
            </div>
          ) : (
            <div className="space-y-1">
              {recentTasks.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-center justify-between p-2 border border-slate-800/50 hover:border-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    {getStatusIcon(activity.status)}
                    <div>
                      <div className="text-xs font-medium text-slate-300 font-mono">{activity.target}</div>
                      <div className="text-[10px] text-slate-600">{activity.type}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-slate-600">{activity.timestamp}</span>
                    {activity.riskScore !== undefined && (
                      <span className={cn("text-[10px] font-mono font-medium", getRiskColor(activity.riskScore))}>
                        {(activity.riskScore * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom Row: Risk Distribution + System Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
          <div className="border border-slate-800 bg-slate-900/60 p-4 lg:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Risk Distribution</h2>
            </div>
            {graphStats.nodes === 0 ? (
              <div className="text-xs text-slate-600 py-2 font-mono">
                No risk data available — graph is empty
              </div>
            ) : (
              <div className="space-y-2">
                {[
                  { label: "Critical", count: criticalCount, color: "bg-red-500", pct: graphStats.nodes > 0 ? `${Math.round((criticalCount / graphStats.nodes) * 100)}%` : "0%" },
                  { label: "High", count: highCount, color: "bg-amber-500", pct: graphStats.nodes > 0 ? `${Math.round((highCount / graphStats.nodes) * 100)}%` : "0%" },
                  { label: "Medium", count: mediumCount, color: "bg-cyan-500", pct: graphStats.nodes > 0 ? `${Math.round((mediumCount / graphStats.nodes) * 100)}%` : "0%" },
                  { label: "Low", count: lowCount, color: "bg-emerald-500", pct: graphStats.nodes > 0 ? `${Math.round((lowCount / graphStats.nodes) * 100)}%` : "0%" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between text-[10px] mb-1">
                      <span className="text-slate-400 uppercase tracking-wider">{item.label}</span>
                      <span className="text-slate-500 font-mono">{item.count} entities</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 overflow-hidden">
                      <div className={cn("h-full", item.color)} style={{ width: item.pct }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Lock className="w-3.5 h-3.5 text-cyan-400" />
              <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">System Status</h2>
            </div>
            <div className="space-y-2">
              {[
                { label: "Neo4j", status: graphStats.nodes >= 0 ? "connected" : "disconnected", ok: true },
                { label: "Redis", status: "connected", ok: true },
                { label: "Celery Worker", status: isRunning ? "active" : "idle", ok: true },
                { label: "API Gateway", status: "operational", ok: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-[10px]">
                  <span className="text-slate-500">{item.label}</span>
                  <div className="flex items-center gap-1">
                    <div className={cn("w-1.5 h-1.5 rounded-full", item.ok ? "bg-emerald-400" : "bg-red-400")} />
                    <span className="text-slate-400 font-mono">{item.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Result slide-over panel */}
      <ResultPanel
        isOpen={resultPanelOpen}
        onClose={() => setResultPanelOpen(false)}
      />
    </div>
  );
}
