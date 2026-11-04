type Props = {
  left: number | null | undefined;
  center: number | null | undefined;
  right: number | null | undefined;
  critical?: number;
  neutral?: number;
  supportive?: number;
  className?: string;
  compact?: boolean;
};

export function BiasBar({
  left,
  center,
  right,
  critical,
  neutral,
  supportive,
  className = "",
  compact,
}: Props) {
  const l = critical ?? left ?? 0;
  const c = neutral ?? center ?? 0;
  const r = supportive ?? right ?? 0;
  const total = l + c + r || 1;
  const lp = (l / total) * 100;
  const cp = (c / total) * 100;
  const rp = (r / total) * 100;

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div
        className={`flex w-full overflow-hidden bg-foreground/10 ${compact ? "h-1.5" : "h-2"}`}
        role="img"
        aria-label={`Government framing Critical ${Math.round(lp)}%, Neutral ${Math.round(cp)}%, Supportive ${Math.round(rp)}%`}
      >
        <div style={{ width: `${lp}%`, background: "#8c1d1d" }} title="Critical" />
        <div style={{ width: `${cp}%`, background: "rgb(28 25 23 / 0.55)" }} title="Neutral" />
        <div style={{ width: `${rp}%`, background: "rgb(28 25 23 / 0.18)" }} title="Supportive" />
      </div>
      <div
        className={`flex justify-between gap-2 font-medium ${
          compact ? "text-[10px]" : "text-[11px]"
        }`}
      >
        <span className="text-accent">Critical {Math.round(lp)}%</span>
        <span className="text-foreground">Neutral {Math.round(cp)}%</span>
        <span className="text-foreground/70">Supportive {Math.round(rp)}%</span>
      </div>
    </div>
  );
}
