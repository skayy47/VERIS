"use client";

// TODO(W3): fetch live eval metrics from backend /api/metrics endpoint
const STUB_METRICS = [
  { label: "Faithfulness", value: "—" },
  { label: "Citation Acc", value: "—" },
  { label: "Avg Latency", value: "—" },
  { label: "Avg Cost", value: "—" },
];

export function BenchBar() {
  return (
    <div
      className="px-6 py-2 flex gap-8 text-xs"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      {STUB_METRICS.map((m) => (
        <span key={m.label} style={{ color: "var(--color-muted)" }}>
          {m.label}:{" "}
          <span style={{ color: "var(--color-accent-2)" }}>{m.value}</span>
        </span>
      ))}
    </div>
  );
}
