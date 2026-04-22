"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, LayoutList, Network, ShieldAlert, Timer, Radar, Cpu, PlayCircle } from "lucide-react";
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
    <div className="h-full overflow-y-auto bg-transparent">
      <div className="max-w-[1400px] mx-auto p-4 md:p-8 space-y-6">
        <div className="soc-panel rounded-2xl p-6 relative overflow-hidden backdrop-blur-2xl bg-white/5 border border-white/10 shadow-2xl">
          <div className="absolute top-0 right-0 p-8 w-64 h-64 bg-indigo-500/20 blur-3xl rounded-full" />
          <div className="flex items-start justify-between gap-6 relative z-10">
            <div>
              <div className="text-[11px] uppercase font-semibold tracking-wider text-indigo-400 mb-2">Operation Center</div>
              <h1 className="text-3xl font-bold text-white mt-1 tracking-tight">Aurora Investigation</h1>
              <p className="text-sm text-slate-300 mt-2 max-w-2xl leading-relaxed">
                Execute intelligent OSINT playbooks to normalize data, run graph enrichment modules, and output operational reports.
              </p>
            </div>
            <div className="hidden md:flex items-center gap-3 text-xs text-slate-300 font-semibold uppercase tracking-wider">
              <div className="inline-flex items-center gap-2 px-4 py-2 border border-cyan-500/30 bg-cyan-500/10 rounded-xl">
                <Radar className="w-3 h-3 text-cyan-600" /> ACTIVE
              </div>
              <div className="inline-flex items-center gap-2 px-4 py-2 border border-violet-500/30 bg-violet-500/10 rounded-xl">
                <Cpu className="w-3 h-3 text-violet-600" /> MODULES
              </div>
            </div>
          </div>
          <div className="mt-6">
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
                    setModuleResult(playbookId, module, data);
                  },
                  (module, status, error) => {
                    if (error || status === "failure") {
                      setModuleStatus(playbookId, module, "error", error ?? "failed");
                    } else {
                      setModuleStatus(playbookId, module, "done");
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
                  },
                  modules,
                  (module, text) => {
                    const label = moduleLabels?.[module] ?? module;
                    appendLog(`\x1b[36m[${label}]\x1b[0m ${text}`);
                  }
                );
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="soc-panel-dense rounded-sm p-4">
            <div className="flex items-center justify-between">
              <Network className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Entities</span>
            </div>
            <p className="text-2xl font-mono text-slate-200 mt-3">{graphStats.nodes}</p>
          </div>
          <div className="soc-panel-dense rounded-sm p-4">
            <div className="flex items-center justify-between">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Relations</span>
            </div>
            <p className="text-2xl font-mono text-slate-200 mt-3">{graphStats.edges}</p>
          </div>
          <div className="soc-panel-dense rounded-sm p-4">
            <div className="flex items-center justify-between">
              <Timer className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Running</span>
            </div>
            <p className="text-2xl font-mono text-slate-200 mt-3">{totalRunningModules}</p>
          </div>
          <div className="soc-panel-dense rounded-sm p-4">
            <div className="flex items-center justify-between">
              <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Results</span>
            </div>
            <button
              onClick={() => setResultPanelOpen(true)}
              className="mt-3 inline-flex items-center gap-2 text-[11px] font-mono hover:text-slate-200 transition-colors uppercase tracking-widest text-slate-400"
            >
              <LayoutList className="w-3 h-3" />
              Open Panel
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="soc-panel-dense rounded-sm p-5 border-sharp">
            <h2 className="text-[11px] uppercase tracking-widest font-mono text-slate-500">Operation Snapshot</h2>
            <div className="mt-3 text-xs text-slate-400 space-y-1 font-mono">
              <p>Graph sync   : <span className="text-slate-300">{graphStats.refreshedAt || "n/a"}</span></p>
              <p>Active traces: <span className="text-slate-300">{Object.keys(resultStore).length}</span></p>
              <p>Stream status: <span className="text-emerald-500">online</span></p>
            </div>
          </div>
          <div className="soc-panel-dense rounded-sm p-5 border-sharp">
            <h2 className="text-[11px] uppercase tracking-widest font-mono text-slate-500">Execution Flow</h2>
            <div className="mt-3 space-y-2 text-xs font-mono">
              {[
                "1. Target triage and classification",
                "2. Dispatch scalable celery queues",
                "3. Intercept & normalize artifacts",
                "4. Stream graph / report updates",
              ].map((step) => (
                <div key={step} className="flex items-center gap-2 text-slate-400">
                  <PlayCircle className="w-3 h-3 text-slate-600" />
                  {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <ResultPanel isOpen={resultPanelOpen} onClose={() => setResultPanelOpen(false)} />
    </div>
  );
}
