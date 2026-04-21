"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, LayoutList, Network, ShieldAlert, Timer } from "lucide-react";
import { fetchGraph, getPlaybookPlan, createPlaybookStream } from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";
import { ResultPanel } from "@/components/ResultPanel";
import { Omnibar } from "@/components/Omnibar";

export default function DashboardPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [resultPanelOpen, setResultPanelOpen] = useState(false);
  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0, refreshedAt: "" });

  const appendLog = useInvestigationStore((s) => s.appendLog);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);
  const initPlaybook = useInvestigationStore((s) => s.initPlaybook);
  const setModuleStatus = useInvestigationStore((s) => s.setModuleStatus);
  const setModuleResult = useInvestigationStore((s) => s.setModuleResult);
  const resultStore = useInvestigationStore((s) => s.resultStore);
  const setStatus = useInvestigationStore((s) => s.setStatus);
  const totalRunningModules = useMemo(
    () =>
      Object.values(resultStore).reduce(
        (sum, pb) =>
          sum + Object.values(pb.modules).filter((m) => m.status === "pending" || m.status === "running").length,
        0
      ),
    [resultStore]
  );

  const refreshStats = useCallback(async () => {
    try {
      const data = await fetchGraph();
      setGraphStats({
        nodes: data.nodes?.length ?? 0,
        edges: data.edges?.length ?? 0,
        refreshedAt: new Date().toLocaleTimeString(),
      });
      setGraphData(data);
    } catch {
      // non-blocking
    }
  }, [setGraphData]);
  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <h1 className="text-2xl font-semibold text-slate-100">Investigation Command</h1>
          <p className="text-sm text-slate-400 mt-1">Unified smart search and live playbook orchestration.</p>
          <div className="mt-5">
            <Omnibar
              loading={isRunning}
              onLoadingChange={setIsRunning}
              onResult={({ playbookId, target, types, modules, moduleLabels }) => {
                const pendingPlan: Record<string, { module: string; task_id: string; status: string; label?: string }> = {};
                modules.forEach((m) => {
                  pendingPlan[m] = { module: m, task_id: "", status: "pending", label: moduleLabels?.[m] ?? m };
                });
                initPlaybook(playbookId, target, types, pendingPlan);
                setStatus("running");
                setResultPanelOpen(true);
                appendLog(`[Playbook] Started ${playbookId} target=${target}`);
                getPlaybookPlan(playbookId)
                  .then((plan) => {
                    if (Object.keys(plan).length > 0) initPlaybook(playbookId, target, types, plan);
                  })
                  .catch(() => undefined);
                createPlaybookStream(
                  playbookId,
                  (module, data) => {
                    const moduleKey = module.startsWith("tasks.") ? module : `tasks.${module}`;
                    setModuleResult(playbookId, moduleKey, data);
                  },
                  (module, status, error) => {
                    const moduleKey = module.startsWith("tasks.") ? module : `tasks.${module}`;
                    if (error || status === "failure") {
                      setModuleStatus(playbookId, moduleKey, "error", error ?? "failed");
                    } else {
                      setModuleStatus(playbookId, moduleKey, "done");
                    }
                  },
                  () => {
                    appendLog(`[Playbook] Completed ${playbookId}`);
                    setStatus("done");
                    setIsRunning(false);
                    refreshStats();
                  },
                  (err) => {
                    appendLog(`[WS Error] ${err}`);
                    setStatus("error");
                  }
                );
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <Network className="w-4 h-4 text-cyan-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Entities</span>
            </div>
            <p className="text-2xl font-mono text-slate-100 mt-3">{graphStats.nodes}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <Activity className="w-4 h-4 text-violet-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Relations</span>
            </div>
            <p className="text-2xl font-mono text-slate-100 mt-3">{graphStats.edges}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <Timer className="w-4 h-4 text-amber-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Running</span>
            </div>
            <p className="text-2xl font-mono text-slate-100 mt-3">{totalRunningModules}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Results</span>
            </div>
            <button
              onClick={() => setResultPanelOpen(true)}
              className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-cyan-300 hover:text-cyan-100"
            >
              <LayoutList className="w-3.5 h-3.5" />
              Open Results Panel
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="text-sm font-semibold text-slate-200">Operational Snapshot</h2>
          <div className="mt-3 text-xs text-slate-400 space-y-1">
            <p>Graph refresh: <span className="font-mono text-slate-300">{graphStats.refreshedAt || "n/a"}</span></p>
            <p>Active playbooks: <span className="font-mono text-slate-300">{Object.keys(resultStore).length}</span></p>
            <p>Stream health: <span className="font-mono text-emerald-300">online</span></p>
          </div>
        </div>
      </div>
      <ResultPanel isOpen={resultPanelOpen} onClose={() => setResultPanelOpen(false)} />
    </div>
  );
}
