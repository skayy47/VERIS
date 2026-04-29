"use client";

import { AuroraBackground } from "@/components/background/AuroraBackground";
import { BenchBar } from "@/components/layout/BenchBar";
import { Header } from "@/components/layout/Header";
import { CitationsPanel } from "@/components/research/CitationsPanel";
import { MetricsSidebar } from "@/components/research/MetricsSidebar";
import { QueryPanel } from "@/components/research/QueryPanel";
import { StreamingReasoning } from "@/components/research/StreamingReasoning";
import { postResearch } from "@/lib/api";
import { useResearchStore } from "@/lib/store";
import type { AgentStateUpdate, Citation, Metrics } from "@/lib/types";

export default function ResearchPage() {
  const { appendStep, setStreaming, setError, reset, setCitations, setMetrics, steps, citations, metrics, isStreaming } =
    useResearchStore();

  const handleSubmit = async (query: string) => {
    reset();
    setStreaming(true);
    try {
      const resp = await postResearch({ query, language: "en" });
      if (!resp.body) throw new Error("No response body");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const update: AgentStateUpdate = JSON.parse(line.slice(6));
              appendStep(update);
              if (update.state === "answer" && update.metadata) {
                const meta = update.metadata;
                if (Array.isArray(meta.citations)) {
                  setCitations(meta.citations as Citation[]);
                }
                if (meta.metrics && typeof meta.metrics === "object") {
                  setMetrics(meta.metrics as Metrics);
                }
              }
            } catch {
              // skip malformed SSE frame
            }
          }
        }
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="relative min-h-screen" style={{ backgroundColor: "var(--color-void)" }}>
      <AuroraBackground />
      <div className="relative z-10 flex flex-col min-h-screen">
        <Header />
        <BenchBar />
        <main className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 p-4 max-w-7xl mx-auto w-full">
          <div className="flex flex-col gap-4">
            <QueryPanel onSubmit={handleSubmit} isLoading={isStreaming} />
            <StreamingReasoning steps={steps} isStreaming={isStreaming} />
            <CitationsPanel citations={citations} />
          </div>
          <MetricsSidebar metrics={metrics} />
        </main>
      </div>
    </div>
  );
}
