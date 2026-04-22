"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import anser from "anser";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInvestigationStore } from "@/store/useInvestigationStore";

export function GlobalTerminal() {
  const containerRef = useRef<HTMLPreElement>(null);
  const [height, setHeight] = useState(160);
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
      const newH = Math.min(320, Math.max(60, startH.current + delta));
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
    <div className="overflow-hidden flex flex-col border-t border-white/[0.05] bg-white/[0.01] backdrop-blur-md">
      {/* Drag handle + collapse header */}
      <div
        className="flex items-center justify-between px-4 py-2 cursor-ns-resize select-none border-b border-white/[0.05] bg-white/[0.02]"
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
          <Terminal className="w-3 h-3 text-indigo-400" />
          <span className="text-[11px] font-semibold text-slate-300 tracking-wide uppercase">Aurora Console</span>
          {streamLog.length > 0 && (
            <span className="text-[9px] text-slate-700 tabular-nums">{streamLog.length} lines</span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <button onClick={clearLog} className="p-1 text-slate-600 hover:text-slate-400 transition-colors text-[10px]">
            Clear
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
            className="p-1 text-slate-600 hover:text-slate-400 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Log content */}
      {expanded && (
        <pre
          ref={containerRef}
          className="flex-1 overflow-auto font-mono text-[11px] text-slate-300 px-4 py-2 leading-[1.55]"
          style={{ height, minHeight: 48 }}
        >
          {displayLines.length === 0 && (
            <span className="text-slate-700 italic">Ready — enter a target to begin investigation.</span>
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
