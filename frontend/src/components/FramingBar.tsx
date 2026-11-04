import type { FramingCounts } from "@/lib/api";
import { FRAMING_COLORS, FRAMING_LABELS } from "@/lib/framing";
import { cn } from "@/lib/utils";

const ORDER: (keyof FramingCounts)[] = [
  "government_critical",
  "government_neutral",
  "government_supportive",
  "insufficient_evidence",
  "analysis_unavailable",
  "unclassified",
];

export function FramingBar({
  counts,
  total,
  className,
  height = "h-2.5",
}: {
  counts: Partial<FramingCounts>;
  total?: number;
  className?: string;
  height?: string;
}) {
  const sum =
    total ??
    ORDER.reduce((acc, key) => acc + (counts[key] ?? 0), 0);

  if (sum === 0) {
    return <div className={cn("w-full bg-foreground/10", height, className)} />;
  }

  return (
    <div
      className={cn("flex w-full overflow-hidden bg-foreground/10", height, className)}
      role="img"
      aria-label="Government framing distribution"
    >
      {ORDER.map((key) => {
        const value = counts[key] ?? 0;
        if (value <= 0) return null;
        return (
          <div
            key={key}
            className={cn("h-full", FRAMING_COLORS[key])}
            style={{ width: `${(value / sum) * 100}%` }}
            title={`${FRAMING_LABELS[key] ?? key}: ${value}`}
          />
        );
      })}
    </div>
  );
}
