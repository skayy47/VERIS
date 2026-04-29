import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VERIS — Production Research Agent",
  description: "Multi-step AI research agent with citations, eval gate, and ops observability.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
