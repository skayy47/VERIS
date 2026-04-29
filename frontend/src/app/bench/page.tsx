"use client";

import { useEffect, useState } from "react";
import { AuroraBackground } from "@/components/background/AuroraBackground";
import { Header } from "@/components/layout/Header";
import { GlowCard } from "@/components/ui/GlowCard";
import { MetricCard } from "@/components/ui/MetricCard";
import type { BenchResult } from "@/lib/types";

const LANG_LABELS: Record<string, string> = { en: "English", fr: "Français", ar: "العربية" };
const TABS = ["all", "en", "fr", "ar"] as const;
type Tab = (typeof TABS)[number];

export default function BenchPage() {
  const [results, setResults] = useState<BenchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("all");

  useEffect(() => {
    fetch("http://localhost:8001/api/bench")
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then(setResults)
      .catch((e: unknown) => setError(String(e)));
  }, []);

  const visible = tab === "all" ? results : results.filter((r) => r.language === tab);

  const avg = (key: keyof BenchResult) =>
    visible.length
      ? (visible.reduce((s, r) => s + (r[key] as number), 0) / visible.length).toFixed(3)
      : "—";

  return (
    <div className="relative min-h-screen" style={{ backgroundColor: "var(--color-void)" }}>
      <AuroraBackground />
      <div className="relative z-10">
        <Header />
        <main className="p-6 max-w-5xl mx-auto space-y-6">
          <h1 className="text-2xl font-bold" style={{ color: "var(--color-accent)" }}>
            VERIS-Bench Leaderboard
          </h1>

          {/* summary metrics */}
          {visible.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <MetricCard label="Avg Faithfulness" value={avg("faithfulness")} />
              <MetricCard label="Avg Cit. Accuracy" value={avg("citation_accuracy")} />
              <MetricCard label="Avg Latency (s)" value={avg("latency_seconds")} />
              <MetricCard label="Avg Cost ($)" value={avg("cost_usd")} />
            </div>
          )}

          {/* language tab strip */}
          <div className="flex gap-2">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="px-3 py-1 rounded text-sm font-medium transition-colors"
                style={{
                  backgroundColor: tab === t ? "var(--color-accent)" : "transparent",
                  color: tab === t ? "var(--color-void)" : "var(--color-muted)",
                  border: "1px solid var(--color-accent)",
                }}
              >
                {t === "all" ? "All" : LANG_LABELS[t] ?? t}
              </button>
            ))}
          </div>

          {error && (
            <p style={{ color: "var(--color-accent-2)" }}>
              {error} — run{" "}
              <code style={{ color: "var(--color-accent)" }}>
                python -m eval.run_eval --sample 5
              </code>{" "}
              first.
            </p>
          )}

          {visible.length === 0 && !error && (
            <p style={{ color: "var(--color-muted)" }}>No results for this filter.</p>
          )}

          {visible.length > 0 && (
            <GlowCard>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" style={{ color: "var(--color-text)" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                      {["ID", "Lang", "Faithful", "CitAcc", "Latency(s)", "Cost($)", "Hops"].map(
                        (h) => (
                          <th key={h} className="py-2 px-3 text-left font-semibold" style={{ color: "var(--color-muted)" }}>
                            {h}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((r) => (
                      <tr
                        key={r.id}
                        style={{ borderBottom: "1px solid var(--color-border)" }}
                        className="hover:bg-white/5 transition-colors"
                      >
                        <td className="py-2 px-3 font-mono" style={{ color: "var(--color-accent)" }}>
                          {r.id}
                        </td>
                        <td className="py-2 px-3">{r.language}</td>
                        <td className="py-2 px-3">{r.faithfulness.toFixed(3)}</td>
                        <td className="py-2 px-3">{r.citation_accuracy.toFixed(3)}</td>
                        <td className="py-2 px-3">{r.latency_seconds.toFixed(2)}</td>
                        <td className="py-2 px-3">{r.cost_usd.toFixed(5)}</td>
                        <td className="py-2 px-3">{r.num_search_hops}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlowCard>
          )}
        </main>
      </div>
    </div>
  );
}
