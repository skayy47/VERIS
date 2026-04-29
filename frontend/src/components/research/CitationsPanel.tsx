"use client";

import { GlowCard } from "@/components/ui/GlowCard";
import type { Citation } from "@/lib/types";

interface CitationsPanelProps {
  citations: Citation[];
}

export function CitationsPanel({ citations }: CitationsPanelProps) {
  if (!citations.length) return null;

  return (
    <GlowCard>
      <p
        className="text-xs uppercase tracking-wider mb-3"
        style={{ color: "var(--color-muted)" }}
      >
        Citations
      </p>
      <ol className="flex flex-col gap-2">
        {citations.map((c) => (
          <li key={c.rank} className="text-sm flex gap-2">
            <span className="shrink-0" style={{ color: "var(--color-accent)" }}>
              [{c.rank}]
            </span>
            <a
              href={c.url}
              target="_blank"
              rel="noopener noreferrer"
              className="truncate hover:underline"
              style={{ color: "var(--color-accent-2)" }}
            >
              {c.title || c.url}
            </a>
          </li>
        ))}
      </ol>
    </GlowCard>
  );
}
