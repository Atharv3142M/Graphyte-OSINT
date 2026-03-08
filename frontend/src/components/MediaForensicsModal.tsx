"use client";

import { useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BoundingBox {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence?: number;
  type: "face" | "object";
}

interface MediaForensicsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  imageUrl?: string | null;
  boxes?: BoundingBox[];
}

export function MediaForensicsModal({
  open,
  onOpenChange,
  imageUrl = "/placeholder-forensics.jpg",
  boxes = [],
}: MediaForensicsModalProps) {
  const handleBoxClick = useCallback((box: BoundingBox) => {
    console.log("Selected:", box);
  }, []);

  const demoBoxes: BoundingBox[] =
    boxes.length > 0
      ? boxes
      : [
          { id: "1", label: "Face", x: 0.2, y: 0.15, width: 0.15, height: 0.2, confidence: 0.94, type: "face" },
          { id: "2", label: "Face", x: 0.55, y: 0.2, width: 0.12, height: 0.18, confidence: 0.89, type: "face" },
          { id: "3", label: "Laptop", x: 0.35, y: 0.5, width: 0.25, height: 0.2, confidence: 0.82, type: "object" },
        ];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <h2 className="font-semibold text-slate-100">Image Forensics</h2>
            <Dialog.Close asChild>
              <button className="p-2 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </Dialog.Close>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <div className="relative inline-block max-w-full">
              <div
                className="relative bg-slate-950 rounded-lg overflow-hidden"
                style={{ aspectRatio: "16/10" }}
              >
                <img
                  src={imageUrl || "https://placehold.co/800x500/1e293b/64748b?text=Forensics+Image"}
                  alt="Forensics"
                  className="w-full h-full object-contain"
                />
                {demoBoxes.map((box) => (
                  <div
                    key={box.id}
                    onClick={() => handleBoxClick(box)}
                    className={cn(
                      "absolute border-2 cursor-pointer transition-all hover:z-10",
                      box.type === "face"
                        ? "border-cyan-500 bg-cyan-500/10 hover:bg-cyan-500/20"
                        : "border-amber-500 bg-amber-500/10 hover:bg-amber-500/20"
                    )}
                    style={{
                      left: `${box.x * 100}%`,
                      top: `${box.y * 100}%`,
                      width: `${box.width * 100}%`,
                      height: `${box.height * 100}%`,
                    }}
                  >
                    <span className="absolute -top-6 left-0 text-xs font-medium px-1.5 py-0.5 rounded bg-slate-900 border border-slate-600">
                      {box.label} {box.confidence ? `(${(box.confidence * 100).toFixed(0)}%)` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-4 flex gap-4 text-sm">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded border-2 border-cyan-500" />
                Face
              </span>
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded border-2 border-amber-500" />
                Object
              </span>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
