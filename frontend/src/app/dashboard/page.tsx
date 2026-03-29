"use client";

import { useState, useCallback } from "react";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { investigate, runModule, createTaskStream, fetchGraph, type ModuleEndpoint } from "@/lib/api";
import { useInvestigationStore } from "@/store/useInvestigationStore";

type WorkflowIntensity = "low" | "standard" | "aggressive" | "agent";

const INTENSITIES: { value: WorkflowIntensity; label: string; color: string }[] = [
  { value: "low", label: "Passive", color: "text-emerald-400" },
  { value: "standard", label: "Standard", color: "text-cyan-400" },
  { value: "aggressive", label: "Aggressive", color: "text-amber-400" },
  { value: "agent", label: "AI Agent", color: "text-violet-400" },
];

interface RecentActivity {
  id: string;
  target: string;
  type: string;
  status: "completed" | "running" | "failed";
  timestamp: string;
  riskScore?: number;
}

const RECENT_ACTIVITIES: RecentActivity[] = [
  { id: "1", target: "example.com", type: "DNS Intel", status: "completed", timestamp: "2 min ago", riskScore: 0.23 },
  { id: "2", target: "192.168.1.1", type: "Port Scan", status: "completed", timestamp: "15 min ago", riskScore: 0.67 },
  { id: "3", target: "test-site.org", type: "SSL Analysis", status: "running", timestamp: "Just now" },
  { id: "4", target: "admin.io", type: "WHOIS", status: "completed", timestamp: "1 hour ago", riskScore: 0.12 },
  { id: "5", target: "suspicious.net", type: "HTTP Security", status: "failed", timestamp: "2 hours ago" },
];

export default function DashboardPage() {
  const [target, setTarget] = useState("");
  const [intensity, setIntensity] = useState<WorkflowIntensity>("standard");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const appendLog = useInvestigationStore((s) => s.appendLog);
  const setGraphData = useInvestigationStore((s) => s.setGraphData);
  const setStatus = useInvestigationStore((s) => s.setStatus);

  const handleInvestigate = useCallback(async () => {
    if (!target.trim()) return;
    setIsRunning(true);
    appendLog(`\x1b[35m[Dashboard]\x1b[0m Starting investigation: "${target}"`);

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
      } else {
        const endpoints: Partial<Record<WorkflowIntensity, ModuleEndpoint>> = {
          low: "/api/dns-intel",
          standard: "/api/shodan",
          aggressive: "/api/port-scan",
        };
        const endpoint = endpoints[intensity];
        if (!endpoint) {
          appendLog("\x1b[31m[Error]\x1b[0m Invalid intensity selection");
          setIsRunning(false);
          return;
        }
        const res = await runModule(endpoint, { target, domain: target, host: target });
        appendLog(`\x1b[36m[Task]\x1b[0m ${res.task_id}`);
        const ws = createTaskStream(res.task_id, (_raw, parsed) => {
          if (parsed?.type === "done") {
            setIsRunning(false);
            fetchGraph().then(setGraphData).catch(console.error);
          }
        });
        appendLog(`\x1b[90mStream: ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/ws/task/${res.task_id}\x1b[0m`);
        return () => ws.close();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog(`\x1b[31m[Error]\x1b[0m ${msg}`);
      setStatus("error");
    } finally {
      setIsRunning(false);
    }
  }, [target, intensity, appendLog, setGraphData, setStatus]);

  const currentIntensity = INTENSITIES.find((i) => i.value === intensity)!;

  const stats = [
    { label: "Total Scans", value: "1,247", change: "+12%", icon: Database, color: "text-cyan-400" },
    { label: "Active Threats", value: "23", change: "-5%", icon: Shield, color: "text-red-400" },
    { label: "Avg Risk Score", value: "0.42", change: "+0.03", icon: TrendingUp, color: "text-amber-400" },
    { label: "Entities Mapped", value: "8,432", change: "+234", icon: Globe, color: "text-violet-400" },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case "running": return <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />;
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

  return (
    <div className="h-full overflow-y-auto bg-slate-950">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
            <p className="text-sm text-slate-400 mt-1">Overview of your OSINT investigations</p>
          </div>
        </div>

        {/* Quick Investigation */}
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Quick Investigation</h2>
          </div>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleInvestigate()}
                placeholder="Enter IP, domain, URL, or email..."
                disabled={isRunning}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-colors"
              />
            </div>
            <div className="relative">
              <button
                onClick={() => setDropdownOpen((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium bg-white/5 hover:bg-white/10 transition-colors border border-slate-700"
              >
                <span className={currentIntensity.color}>{currentIntensity.label}</span>
              </button>
              {dropdownOpen && (
                <div className="absolute top-full left-0 mt-2 glass-panel rounded-xl py-1 min-w-[120px] z-50 animate-fade-in-up">
                  {INTENSITIES.map((i) => (
                    <button
                      key={i.value}
                      onClick={() => {
                        setIntensity(i.value);
                        setDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-2 text-xs font-medium hover:bg-white/5 transition-colors",
                        i.color,
                        intensity === i.value && "bg-white/5"
                      )}
                    >
                      {i.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={handleInvestigate}
              disabled={isRunning || !target.trim()}
              className={cn(
                "px-6 py-2.5 rounded-xl text-sm font-semibold transition-all",
                isRunning
                  ? "bg-slate-800 text-slate-500 cursor-wait"
                  : "bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white shadow-lg shadow-cyan-500/20"
              )}
            >
              {isRunning ? "Running..." : "Investigate"}
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="glass-panel rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <stat.icon className={cn("w-5 h-5", stat.color)} />
                <span className={cn("text-xs font-medium", stat.change.startsWith("+") ? "text-emerald-400" : "text-red-400")}>
                  {stat.change}
                </span>
              </div>
              <div className="text-2xl font-bold text-slate-100">{stat.value}</div>
              <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Recent Activity */}
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold text-slate-200">Recent Activity</h2>
            </div>
            <button className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">View All</button>
          </div>
          <div className="space-y-2">
            {RECENT_ACTIVITIES.map((activity) => (
              <div
                key={activity.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-800/30 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(activity.status)}
                  <div>
                    <div className="text-sm font-medium text-slate-200">{activity.target}</div>
                    <div className="text-xs text-slate-500">{activity.type}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-500">{activity.timestamp}</span>
                  {activity.riskScore !== undefined && (
                    <div className="flex items-center gap-2">
                      <Shield className="w-3.5 h-3.5 text-slate-500" />
                      <span className={cn("text-xs font-medium", getRiskColor(activity.riskScore))}>
                        {(activity.riskScore * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="glass-panel rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold text-slate-200">Risk Distribution</h2>
            </div>
            <div className="space-y-3">
              {[
                { label: "Critical", count: 12, color: "bg-red-500", pct: "15%" },
                { label: "High", count: 45, color: "bg-amber-500", pct: "35%" },
                { label: "Medium", count: 89, color: "bg-cyan-500", pct: "45%" },
                { label: "Low", count: 156, color: "bg-emerald-500", pct: "70%" },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-400">{item.label}</span>
                    <span className="text-slate-300">{item.count} entities</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div className={cn("h-full rounded-full", item.color)} style={{ width: item.pct }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold text-slate-200">Security Posture</h2>
            </div>
            <div className="flex items-center justify-center h-32">
              <div className="text-center">
                <div className="text-4xl font-bold text-emerald-400">72</div>
                <div className="text-xs text-slate-500 mt-1">Overall Security Score</div>
                <div className="text-xs text-emerald-400 mt-2">+8 from last week</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
