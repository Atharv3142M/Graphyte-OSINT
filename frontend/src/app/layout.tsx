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
        <div className="h-screen w-screen overflow-hidden flex">
          {/* Left Sidebar - Global Navigation */}
          <div className="flex-shrink-0 z-40">
            <AppSidebar />
          </div>

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Page Content */}
            <main className="flex-1 overflow-hidden">
              {children}
            </main>

            {/* Global Terminal - Bottom */}
            <div className="flex-shrink-0 z-40">
              <GlobalTerminal />
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
