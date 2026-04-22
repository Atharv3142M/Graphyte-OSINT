import type { Metadata } from "next";
import "./globals.css";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { GlobalTerminal } from "@/components/layout/GlobalTerminal";
import { Activity, Shield } from "lucide-react";

export const metadata: Metadata = {
  title: "OSINT Footprint Visualizer",
  description: "Professional OSINT Digital Footprint Visualizer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="h-screen w-screen overflow-hidden flex bg-transparent text-slate-100">
          <div className="flex-shrink-0 z-30">
            <AppSidebar />
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-14 border-b border-white/[0.05] px-6 flex items-center justify-between bg-white/[0.02] backdrop-blur-md">
              <div>
                <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">OSINT Digital Footprint Visualizer</div>
                <div className="text-sm text-slate-300 mt-0.5">Aurora Operational Environment</div>
              </div>
              <div className="flex items-center gap-5 text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  Services online
                </div>
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Shield className="w-3.5 h-3.5 text-cyan-400" />
                  Protection active
                </div>
              </div>
            </header>
            <main className="flex-1 overflow-hidden bg-transparent">
              {children}
            </main>
            <div className="flex-shrink-0 z-40">
              <GlobalTerminal />
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
