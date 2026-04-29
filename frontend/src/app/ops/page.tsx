"use client";

import { AuroraBackground } from "@/components/background/AuroraBackground";
import { Header } from "@/components/layout/Header";

export default function OpsPage() {
  return (
    <div className="relative min-h-screen" style={{ backgroundColor: "var(--color-void)" }}>
      <AuroraBackground />
      <div className="relative z-10">
        <Header />
        <main className="p-8">
          <h1 className="text-2xl font-bold mb-4" style={{ color: "var(--color-accent)" }}>
            Ops Dashboard
          </h1>
          {/* TODO(W3): replace with NEXT_PUBLIC_GRAFANA_URL from env */}
          <iframe
            src="http://localhost:3030"
            className="w-full rounded"
            style={{ height: "80vh", border: "1px solid var(--color-border)" }}
            title="Grafana Dashboard"
          />
        </main>
      </div>
    </div>
  );
}
