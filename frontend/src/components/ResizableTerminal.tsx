"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import anser from "anser";
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ResizableTerminalProps {
  lines: string[];
  className?: string;
  maxLines?: number;
  defaultHeight?: number;
  minHeight?: number;
  maxHeight?: number;
}

export function ResizableTerminal({
  lines,
  className = "",
  maxLines = 500,
  defaultHeight = 200,
  minHeight = 120,
  maxHeight = 480,
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
    <div className={cn("flex flex-col border-t border-slate-700 bg-slate-950", className)}>
      <div
        className="flex items-center justify-center h-2 cursor-ns-resize hover:bg-slate-800/50 transition-colors group"
        onMouseDown={(e) => {
          setDragging(true);
          startY.current = e.clientY;
          startH.current = height;
        }}
      >
        <GripVertical className="w-4 h-4 text-slate-500 group-hover:text-slate-400" />
      </div>
      <pre
        ref={containerRef}
        className="flex-1 overflow-auto font-mono text-xs text-slate-200 p-3"
        style={{ height, minHeight: 80 }}
      >
        {displayLines.map((raw, i) => {
          const escaped = raw.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
          const html = anser.ansiToHtml(escaped, { use_classes: true });
          return (
            <div key={i} className="leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />
          );
        })}
      </pre>
    </div>
  );
}
