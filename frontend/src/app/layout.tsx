import type { Metadata } from "next";
import "./globals.css";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { GlobalTerminal } from "@/components/layout/GlobalTerminal";

export const metadata: Metadata = {
  title: "OSINT Command Center",
  description: "Enterprise OSINT Digital Footprint Visualizer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="h-screen w-screen overflow-hidden flex bg-slate-950">
          <div className="flex-shrink-0 z-40">
            <AppSidebar />
          </div>
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-12 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-950/80 backdrop-blur">
              <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Open Source Intelligence Platform</div>
              <div className="text-xs text-slate-400 font-mono">live workspace</div>
            </header>
            <main className="flex-1 overflow-hidden bg-slate-950">
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
