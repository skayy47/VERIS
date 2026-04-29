"use client";

import { useState } from "react";
import { GlowCard } from "@/components/ui/GlowCard";
import { NeonButton } from "@/components/ui/NeonButton";

interface QueryPanelProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export function QueryPanel({ onSubmit, isLoading }: QueryPanelProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSubmit(query.trim());
  };

  return (
    <GlowCard>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label
          className="text-xs uppercase tracking-wider"
          style={{ color: "var(--color-muted)" }}
        >
          Research Query
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What are the latest advances in transformer architecture scaling?"
          rows={3}
          disabled={isLoading}
          className="w-full rounded p-3 text-sm resize-none focus:outline-none"
          style={{
            backgroundColor: "var(--color-void)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
          }}
        />
        <NeonButton type="submit" disabled={isLoading || !query.trim()}>
          {isLoading ? "Researching..." : "Research"}
        </NeonButton>
      </form>
    </GlowCard>
  );
}
