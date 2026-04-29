interface MetricCardProps {
  label: string;
  value: string | number | null;
  unit?: string;
}

export function MetricCard({ label, value, unit }: MetricCardProps) {
  return (
    <div
      className="flex flex-col gap-1 p-3 rounded"
      style={{
        backgroundColor: "var(--color-surface-2)",
        border: "1px solid var(--color-border)",
      }}
    >
      <span className="text-xs" style={{ color: "var(--color-muted)" }}>
        {label}
      </span>
      <span className="text-lg font-bold" style={{ color: "var(--color-accent-2)" }}>
        {value !== null && value !== undefined ? String(value) : "—"}
        {unit && value !== null && value !== undefined && (
          <span className="text-xs ml-1" style={{ color: "var(--color-muted)" }}>
            {unit}
          </span>
        )}
      </span>
    </div>
  );
}
