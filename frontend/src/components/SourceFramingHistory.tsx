import { FRAMING_COLORS, FRAMING_LABELS } from "@/lib/framing";

export function SourceFramingHistory({
  history,
}: {
  history: Record<string, number> | null;
}) {
  if (!history || Object.keys(history).length === 0) {
    return <span className="text-xs text-foreground/45">No framing history yet</span>;
  }

  const total = Object.values(history).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-1">
      <div className="flex h-2 w-full max-w-[140px] overflow-hidden rounded-full bg-surface-muted">
        {Object.entries(history).map(([key, count]) => (
          <div
            key={key}
            className={FRAMING_COLORS[key] ?? "bg-slate-300"}
            style={{ width: `${(count / total) * 100}%` }}
            title={`${FRAMING_LABELS[key] ?? key}: ${count}`}
          />
        ))}
      </div>
      <p className="text-[10px] text-foreground/45">{total} articles</p>
    </div>
  );
}
