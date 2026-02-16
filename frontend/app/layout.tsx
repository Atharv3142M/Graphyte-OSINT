import React from "react";

export const metadata = {
  title: "OSINT Visualizer",
  description: "Interactive OSINT digital footprint visualizer."
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


