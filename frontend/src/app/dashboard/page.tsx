"use client";

import { useCallback, useEffect, useState } from "react";
import { Sparkles, Wrench } from "lucide-react";
import Link from "next/link";
import { fetchGraph, getPlaybookPlan, createPlaybookStream } from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";
import { Omnibar } from "@/components/Omnibar";
import { InlineResults } from "@/components/InlineResults";

export default function DashboardPage() {
  const [isRunning, setIsRunning] = useState(false);

  const appendLog = useInvestigationStore((s) => s.appendLog);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);
  const initPlaybook = useInvestigationStore((s) => s.initPlaybook);
  const setModuleStatus = useInvestigationStore((s) => s.setModuleStatus);
  const setModuleResult = useInvestigationStore((s) => s.setModuleResult);
  const setStatus = useInvestigationStore((s) => s.setStatus);
  const resultStore = useInvestigationStore((s) => s.resultStore);
  const hasResults = Object.keys(resultStore).length > 0;

  const refreshGraph = useCallback(async () => {
    try {
      const data = await fetchGraph();
      setGraphData(data);
    } catch {
      // non-blocking — graph service may not be up yet
    }
  }, [setGraphData]);

  useEffect(() => {
    refreshGraph();
  }, [refreshGraph]);

  return (
    <div className="h-full overflow-y-auto bg-transparent">
      <div className="max-w-3xl mx-auto px-4 md:px-6 pt-12 pb-24">
        {/* ── Hero (Google-style) ───────────────────────────── */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.03] text-[11px] uppercase tracking-widest text-indigo-300 font-medium mb-6">
            <Sparkles className="w-3 h-3" />
            Graphyte OSINT
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Investigate any target.
          </h1>
          <p className="text-base text-slate-400 mt-3 max-w-xl mx-auto">
            Enter an IP address, domain, email, or username. We&apos;ll run the right
            modules automatically.
          </p>
        </div>

        {/* ── Omnibar ───────────────────────────────────────── */}
        <div className="mb-6">
          <Omnibar
            loading={isRunning}
            onLoadingChange={setIsRunning}
            onResult={({ playbookId, target, types, modules, moduleLabels }) => {
              const pendingPlan: Record<
                string,
                { module: string; task_id: string; status: string; label?: string }
              > = {};
              modules.forEach((m) => {
                pendingPlan[m] = {
                  module: m,
                  task_id: "",
                  status: "pending",
                  label: moduleLabels?.[m] ?? m,
                };
              });
              initPlaybook(playbookId, target, types, pendingPlan);
              setStatus("running");
              appendLog(`[Playbook] Started ${playbookId} target=${target}`);

              getPlaybookPlan(playbookId)
                .then((plan) => {
                  if (Object.keys(plan).length > 0) {
                    initPlaybook(playbookId, target, types, plan);
                  }
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
                  refreshGraph();
                },
                (err) => {
                  appendLog(`[WS Error] ${err}`);
                  setStatus("error");
                },
                modules,
                (module, text) => {
                  const label = moduleLabels?.[module] ?? module;
                  appendLog(`\x1b[36m[${label}]\x1b[0m ${text}`);
                },
              );
            }}
          />
        </div>

        {/* ── Quick hints (only when no results yet) ────────── */}
        {!hasResults ? (
          <div className="text-center text-[12px] text-slate-500 mb-8">
            Looking for the graph view, terminal, or per-module runner? Open the{" "}
            <Link
              href="/workspace"
              className="text-indigo-300 hover:text-indigo-200 underline-offset-2 hover:underline"
            >
              Advanced Workspace
            </Link>{" "}
            or the{" "}
            <Link
              href="/tools"
              className="text-indigo-300 hover:text-indigo-200 underline-offset-2 hover:underline inline-flex items-center gap-1"
            >
              <Wrench className="w-3 h-3" /> Tools
            </Link>{" "}
            page.
          </div>
        ) : null}

        {/* ── Inline results ────────────────────────────────── */}
        <InlineResults />
      </div>
    </div>
  );
}
