"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import anser from "anser";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ResizableTerminalProps {
  lines: string[];
  className?: string;
  maxLines?: number;
  defaultHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  expanded?: boolean;
  onToggle?: () => void;
}

export function ResizableTerminal({
  lines,
  className = "",
  maxLines = 500,
  defaultHeight = 200,
  minHeight = 100,
  maxHeight = 400,
  expanded = true,
  onToggle,
}: ResizableTerminalProps) {
  const containerRef = useRef<HTMLPreElement>(null);
  const [height, setHeight] = useState(defaultHeight);
  const [dragging, setDragging] = useState(false);
  const startY = useRef(0);
  const startH = useRef(0);

  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [lines, scrollToBottom]);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const delta = startY.current - e.clientY;
      const newH = Math.min(maxHeight, Math.max(minHeight, startH.current + delta));
      setHeight(newH);
    };
    const onUp = () => setDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging, minHeight, maxHeight]);

  const displayLines = maxLines > 0 ? lines.slice(-maxLines) : lines;

  return (
    <div className={cn("glass-panel-dense rounded-2xl overflow-hidden flex flex-col", className)}>
      {/* Drag handle + collapse header */}
      <div
        className="flex items-center justify-between px-3 py-2 cursor-ns-resize select-none border-b border-white/[0.04]"
        onMouseDown={(e) => {
          if (e.detail === 2) {
            onToggle?.();
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
          {lines.length > 0 && (
            <span className="text-[10px] text-slate-600 tabular-nums">{lines.length} lines</span>
          )}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          className="p-1 rounded-md hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
        >
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Log content */}
      {expanded && (
        <pre
          ref={containerRef}
          className="flex-1 overflow-auto font-mono text-[11px] text-slate-300 px-3 py-2 leading-[1.7]"
          style={{ height, minHeight: 60 }}
        >
          {displayLines.length === 0 && (
            <span className="text-slate-600 italic">Ready. Enter a target above to begin.</span>
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
