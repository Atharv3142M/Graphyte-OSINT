"use client";

import { X, Shield, Database, Tag, Info } from "lucide-react";
import { cn } from "@/lib/utils";

export interface NodeDetail {
  id: string;
  label?: string;
  type?: string;
  stix?: Record<string, unknown>;
  riskScore?: number;
  entityResolution?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

interface NodeDetailPanelProps {
  node: NodeDetail | null;
  onClose: () => void;
  isOpen: boolean;
}

export function NodeDetailPanel({ node, onClose, isOpen }: NodeDetailPanelProps) {
  if (!node) return null;

  const riskLevel =
    (node.riskScore ?? 0) >= 0.8 ? "critical" : (node.riskScore ?? 0) >= 0.5 ? "warning" : "low";

  const riskColors = {
    critical: { bar: "bg-red-500", text: "text-red-400", glow: "shadow-red-500/30" },
    warning:  { bar: "bg-amber-500", text: "text-amber-400", glow: "shadow-amber-500/30" },
    low:      { bar: "bg-cyan-500", text: "text-cyan-400", glow: "shadow-cyan-500/30" },
  };

  return (
    <div
      className={cn(
        "absolute top-0 right-0 h-full w-[380px] glass-panel-dense border-l border-white/[0.06] shadow-2xl flex flex-col transition-transform duration-300 z-30",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-cyan-500/10 flex items-center justify-center">
            <Info className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <h3 className="font-semibold text-slate-100 text-sm">Entity Details</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Identifier */}
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
            <Database className="w-3 h-3" />
            Identifier
          </div>
          <div className="font-mono text-sm text-cyan-400">{node.id}</div>
          {node.label && (
            <div className="text-sm text-slate-300 mt-1">{node.label}</div>
          )}
        </div>

        {/* Type */}
        {node.type && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              <Tag className="w-3 h-3" />
              Type
            </div>
            <span className="inline-flex px-2.5 py-1 rounded-lg text-xs font-medium bg-white/5 border border-white/[0.06] text-slate-300">
              {node.type}
            </span>
          </div>
        )}

        {/* Risk Score */}
        {node.riskScore !== undefined && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              <Shield className="w-3 h-3" />
              Risk Score
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    riskColors[riskLevel].bar
                  )}
                  style={{ width: `${(node.riskScore ?? 0) * 100}%` }}
                />
              </div>
              <span
                className={cn(
                  "text-sm font-bold tabular-nums",
                  riskColors[riskLevel].text
                )}
              >
                {((node.riskScore ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* STIX */}
        {node.stix && Object.keys(node.stix).length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              STIX 2.1 Metadata
            </div>
            <pre className="text-xs font-mono text-slate-400 bg-black/30 border border-white/[0.04] rounded-xl p-3 overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(node.stix, null, 2)}
            </pre>
          </div>
        )}

        {/* Entity Resolution */}
        {node.entityResolution && Object.keys(node.entityResolution).length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Entity Resolution
            </div>
            <pre className="text-xs font-mono text-slate-400 bg-black/30 border border-white/[0.04] rounded-xl p-3 overflow-x-auto max-h-32 overflow-y-auto">
              {JSON.stringify(node.entityResolution, null, 2)}
            </pre>
          </div>
        )}

        {/* Metadata */}
        {node.metadata && Object.keys(node.metadata).length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Metadata
            </div>
            <dl className="space-y-1.5">
              {Object.entries(node.metadata).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-sm">
                  <dt className="text-slate-500 flex-shrink-0 font-medium">{k}</dt>
                  <dd className="text-slate-300 truncate font-mono text-xs">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
