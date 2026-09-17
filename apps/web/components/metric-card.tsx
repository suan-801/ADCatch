export function MetricCard({ label, value, tone }: { label: string; value: number; tone?: "new" | "active" | "inactive" }) {
  const toneClass =
    tone === "new" ? "text-status-new" : tone === "active" ? "text-status-active" : tone === "inactive" ? "text-status-inactive" : "text-foreground";

  return (
    <div className="rounded border border-border bg-white p-4">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</p>
    </div>
  );
}
