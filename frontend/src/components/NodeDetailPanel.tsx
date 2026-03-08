"use client";

import { X } from "lucide-react";
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

  return (
    <div
      className={cn(
        "absolute top-0 right-0 h-full w-96 border-l border-slate-700 bg-slate-900/95 backdrop-blur-sm shadow-2xl flex flex-col transition-transform duration-300 z-30",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h3 className="font-semibold text-slate-100 text-sm">Entity Details</h3>
        <button
          onClick={onClose}
          className="p-1.5 rounded-md hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Identifier</div>
          <div className="font-mono text-sm text-cyan-400">{node.id}</div>
          {node.label && (
            <div className="text-sm text-slate-300 mt-1">{node.label}</div>
          )}
        </div>

        {node.type && (
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Type</div>
            <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-slate-700 text-slate-300">
              {node.type}
            </span>
          </div>
        )}

        {node.riskScore !== undefined && (
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Risk Score</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    riskLevel === "critical" && "bg-red-500",
                    riskLevel === "warning" && "bg-amber-500",
                    riskLevel === "low" && "bg-cyan-500"
                  )}
                  style={{ width: `${(node.riskScore ?? 0) * 100}%` }}
                />
              </div>
              <span
                className={cn(
                  "text-sm font-medium",
                  riskLevel === "critical" && "text-red-400",
                  riskLevel === "warning" && "text-amber-400",
                  riskLevel === "low" && "text-cyan-400"
                )}
              >
                {((node.riskScore ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {node.stix && Object.keys(node.stix).length > 0 && (
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">STIX 2.1 Metadata</div>
            <pre className="text-xs font-mono text-slate-400 bg-slate-950 rounded-lg p-3 overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(node.stix, null, 2)}
            </pre>
          </div>
        )}

        {node.entityResolution && Object.keys(node.entityResolution).length > 0 && (
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Entity Resolution</div>
            <pre className="text-xs font-mono text-slate-400 bg-slate-950 rounded-lg p-3 overflow-x-auto max-h-32 overflow-y-auto">
              {JSON.stringify(node.entityResolution, null, 2)}
            </pre>
          </div>
        )}

        {node.metadata && Object.keys(node.metadata).length > 0 && (
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Metadata</div>
            <dl className="space-y-1 text-sm">
              {Object.entries(node.metadata).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <dt className="text-slate-500 flex-shrink-0">{k}:</dt>
                  <dd className="text-slate-300 truncate">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
