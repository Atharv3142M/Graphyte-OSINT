"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import anser from "anser";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export function GlobalTerminal() {
  const containerRef = useRef<HTMLPreElement>(null);
  const [height, setHeight] = useState(180);
  const [dragging, setDragging] = useState(false);
  const startY = useRef(0);
  const startH = useRef(0);
  const [expanded, setExpanded] = useState(true);

  const streamLog = useInvestigationStore((s) => s.streamLog);
  const clearLog = useInvestigationStore((s) => s.clearLog);

  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [streamLog, scrollToBottom]);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const delta = startY.current - e.clientY;
      const newH = Math.min(350, Math.max(80, startH.current + delta));
      setHeight(newH);
    };
    const onUp = () => setDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  const displayLines = streamLog.slice(-500);

  return (
    <div className="glass-panel-dense rounded-t-xl overflow-hidden flex flex-col border-t border-white/[0.06]">
      {/* Drag handle + collapse header */}
      <div
        className="flex items-center justify-between px-3 py-2 cursor-ns-resize select-none border-b border-white/[0.04] bg-slate-900/50"
        onMouseDown={(e) => {
          if (e.detail === 2) {
            setExpanded((v) => !v);
            return;
          }
          setDragging(true);
          startY.current = e.clientY;
          startH.current = height;
        }}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-cyan-500" />
          <span className="text-[11px] font-semibold text-slate-400 tracking-wide">Console</span>
          {streamLog.length > 0 && (
            <span className="text-[10px] text-slate-600 tabular-nums">{streamLog.length} lines</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearLog}
            className="p-1 rounded-md hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors text-[10px] px-2"
          >
            Clear
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
            className="p-1 rounded-md hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Log content */}
      {expanded && (
        <pre
          ref={containerRef}
          className="flex-1 overflow-auto font-mono text-[11px] text-slate-300 px-3 py-2 leading-[1.7]"
          style={{ height, minHeight: 60 }}
        >
          {displayLines.length === 0 && (
            <span className="text-slate-600 italic">Ready. Enter a target to begin investigation.</span>
          )}
          {displayLines.map((raw, i) => {
            const escaped = raw
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;");
            const html = anser.ansiToHtml(escaped, { use_classes: true });
            return (
              <div key={i} dangerouslySetInnerHTML={{ __html: html }} />
            );
          })}
        </pre>
      )}
    </div>
  );
}
