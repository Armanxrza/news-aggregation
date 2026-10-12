/** Simple horizontal bar chart from real numeric data — no chart library. */

export function BarChart({
  data,
  maxItems = 12,
}: {
  data: Record<string, number>;
  maxItems?: number;
}) {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxItems);
  const max = entries[0]?.[1] ?? 1;

  if (entries.length === 0) {
    return <p className="text-sm text-foreground/50">No data yet.</p>;
  }

  return (
    <ul className="space-y-2">
      {entries.map(([label, value]) => (
        <li key={label}>
          <div className="mb-0.5 flex justify-between text-xs">
            <span className="font-medium capitalize text-foreground/80">{label}</span>
            <span className="tabular-nums text-foreground/55">{value}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface-muted">
            <div
              className="h-full rounded-full bg-teal-600"
              style={{ width: `${(value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
