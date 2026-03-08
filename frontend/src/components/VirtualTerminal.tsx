"use client";

import { useCallback, useEffect, useRef } from "react";
import anser from "anser";

export interface VirtualTerminalProps {
  lines: string[];
  className?: string;
  maxLines?: number;
}

/**
 * Virtual terminal that renders log lines with ANSI escape code colorization.
 * Uses anser for parsing ANSI sequences.
 */
export function VirtualTerminal({ lines, className = "", maxLines = 500 }: VirtualTerminalProps) {
  const containerRef = useRef<HTMLPreElement>(null);

  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [lines, scrollToBottom]);

  const displayLines = maxLines > 0 ? lines.slice(-maxLines) : lines;

  return (
    <pre
      ref={containerRef}
      className={`font-mono text-xs overflow-auto bg-slate-950 text-slate-200 p-3 rounded-lg border border-slate-700 ${className}`}
      style={{ minHeight: 160, maxHeight: 320 }}
    >
      {displayLines.map((raw, i) => {
        const escaped = raw.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        const html = anser.ansiToHtml(escaped, { use_classes: true });
        return (
          <div
            key={i}
            className="leading-relaxed"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      })}
    </pre>
  );
}
