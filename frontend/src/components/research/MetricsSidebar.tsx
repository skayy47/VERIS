"use client";

import { GlowCard } from "@/components/ui/GlowCard";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Metrics } from "@/lib/types";

interface MetricsSidebarProps {
  metrics: Metrics | null;
}

export function MetricsSidebar({ metrics }: MetricsSidebarProps) {
  return (
    <div className="flex flex-col gap-4">
      <GlowCard>
        <p
          className="text-xs uppercase tracking-wider mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Metrics
        </p>
        <div className="grid grid-cols-2 gap-2">
          <MetricCard
            label="Faithfulness"
            value={metrics?.faithfulness != null ? metrics.faithfulness.toFixed(3) : null}
          />
          <MetricCard
            label="Citation Acc"
            value={metrics?.citation_accuracy != null ? metrics.citation_accuracy.toFixed(3) : null}
          />
          <MetricCard
            label="Latency"
            value={metrics != null ? metrics.latency_seconds.toFixed(2) : null}
            unit="s"
          />
          <MetricCard
            label="Cost"
            value={metrics != null ? metrics.cost_usd.toFixed(5) : null}
            unit="$"
          />
        </div>
      </GlowCard>
      <GlowCard>
        <p
          className="text-xs uppercase tracking-wider mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Models
        </p>
        <div className="flex flex-col gap-1 text-xs" style={{ color: "var(--color-muted)" }}>
          <span>Sonnet 4.6 — complex reasoning</span>
          <span>Haiku 4.5 — fast retrieval</span>
        </div>
      </GlowCard>
    </div>
  );
}
