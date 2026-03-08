"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";

interface ActivityPoint {
  time: string;
  count: number;
  label?: string;
}

interface ActivityTimelineModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data?: ActivityPoint[];
}

const DEMO_DATA: ActivityPoint[] = [
  { time: "00:00", count: 12 },
  { time: "04:00", count: 8 },
  { time: "08:00", count: 45 },
  { time: "12:00", count: 78 },
  { time: "16:00", count: 92 },
  { time: "20:00", count: 65 },
  { time: "24:00", count: 34 },
];

export function ActivityTimelineModal({
  open,
  onOpenChange,
  data = DEMO_DATA,
}: ActivityTimelineModalProps) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-2xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <h2 className="font-semibold text-slate-100">Network Activity Timeline</h2>
            <Dialog.Close asChild>
              <button className="p-2 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </Dialog.Close>
          </div>
          <div className="flex-1 p-4">
            <p className="text-sm text-slate-400 mb-4">
              Frequency of network activity over time (chronological)
            </p>
            <div className="flex items-end gap-1 h-48">
              {data.map((point, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t bg-cyan-500/60 hover:bg-cyan-500/80 transition-colors min-h-[4px]"
                    style={{ height: `${(point.count / maxCount) * 100}%` }}
                    title={`${point.count} events`}
                  />
                  <span className="text-xs text-slate-500">{point.time}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-between text-xs text-slate-500">
              <span>Low</span>
              <span>Activity level</span>
              <span>High</span>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
