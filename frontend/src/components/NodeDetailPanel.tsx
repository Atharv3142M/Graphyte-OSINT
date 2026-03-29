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
    critical: { bar: "bg-red-500", text: "text-red-400" },
    warning:  { bar: "bg-amber-500", text: "text-amber-400" },
    low:      { bar: "bg-cyan-500", text: "text-cyan-400" },
  };

  return (
    <div
      className={cn(
        "absolute top-0 right-0 h-full w-[360px] soc-panel-dense border-l border-slate-800 shadow-2xl flex flex-col transition-transform duration-200 z-30",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 border border-cyan-900 bg-cyan-950/50 flex items-center justify-center">
            <Info className="w-3 h-3 text-cyan-500" />
          </div>
          <h3 className="font-semibold text-slate-200 text-xs uppercase tracking-widest">Entity Details</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-600 hover:text-slate-400 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Identifier */}
        <div>
          <div className="flex items-center gap-1 text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
            <Database className="w-3 h-3" />
            Identifier
          </div>
          <div className="font-mono text-[10px] text-cyan-500 break-all">{node.id}</div>
          {node.label && (
            <div className="text-xs text-slate-300 mt-1 font-mono">{node.label}</div>
          )}
        </div>

        {/* Type */}
        {node.type && (
          <div>
            <div className="flex items-center gap-1 text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
              <Tag className="w-3 h-3" />
              Type
            </div>
            <span className="inline-flex px-2 py-0.5 text-[10px] font-mono border border-slate-800 text-slate-400">
              {node.type}
            </span>
          </div>
        )}

        {/* Risk Score */}
        {node.riskScore !== undefined && (
          <div>
            <div className="flex items-center gap-1 text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
              <Shield className="w-3 h-3" />
              Risk Score
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-slate-800 overflow-hidden">
                <div
                  className={cn(
                    "h-full transition-all duration-500",
                    riskColors[riskLevel].bar
                  )}
                  style={{ width: `${(node.riskScore ?? 0) * 100}%` }}
                />
              </div>
              <span
                className={cn(
                  "text-xs font-bold tabular-nums font-mono",
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
            <div className="text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
              STIX 2.1
            </div>
            <pre className="text-[9px] font-mono text-slate-400 bg-slate-950 border border-slate-800 p-2 overflow-x-auto max-h-40 overflow-y-auto leading-relaxed">
              {JSON.stringify(node.stix, null, 2)}
            </pre>
          </div>
        )}

        {/* Entity Resolution */}
        {node.entityResolution && Object.keys(node.entityResolution).length > 0 && (
          <div>
            <div className="text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
              Entity Resolution
            </div>
            <pre className="text-[9px] font-mono text-slate-400 bg-slate-950 border border-slate-800 p-2 overflow-x-auto max-h-32 overflow-y-auto leading-relaxed">
              {JSON.stringify(node.entityResolution, null, 2)}
            </pre>
          </div>
        )}

        {/* Metadata */}
        {node.metadata && Object.keys(node.metadata).length > 0 && (
          <div>
            <div className="text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">
              Metadata
            </div>
            <dl className="space-y-1">
              {Object.entries(node.metadata).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-[10px]">
                  <dt className="text-slate-600 flex-shrink-0 font-mono w-28 truncate">{k}</dt>
                  <dd className="text-slate-400 font-mono truncate">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
