import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Unified Enterprise OSINT Platform",
  description: "Enterprise OSINT Digital Footprint Visualizer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
