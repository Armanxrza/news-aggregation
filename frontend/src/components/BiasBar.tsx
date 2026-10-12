type Props = {
  left: number | null | undefined;
  center: number | null | undefined;
  right: number | null | undefined;
  critical?: number;
  neutral?: number;
  supportive?: number;
  className?: string;
  compact?: boolean;
  /** Government POV axis (default): Critical · Neutral · Supportive */
  axis?: "government" | "political";
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
  axis = "government",
}: Props) {
  const l = critical ?? left ?? 0;
  const c = neutral ?? center ?? 0;
  const r = supportive ?? right ?? 0;
  const total = l + c + r || 1;
  const lp = (l / total) * 100;
  const cp = (c / total) * 100;
  const rp = (r / total) * 100;

  const labels =
    axis === "government"
      ? { l: "Critical", c: "Neutral", r: "Supportive" }
      : { l: "Left", c: "Centre", r: "Right" };

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div
        className={`flex w-full overflow-hidden rounded-full ${compact ? "h-2" : "h-2.5"}`}
        role="img"
        aria-label={`Gov POV ${labels.l} ${Math.round(lp)}%, ${labels.c} ${Math.round(cp)}%, ${labels.r} ${Math.round(rp)}%`}
      >
        <div className="bg-[#dc2626]" style={{ width: `${lp}%` }} title={labels.l} />
        <div className="bg-[#94a3b8]" style={{ width: `${cp}%` }} title={labels.c} />
        <div className="bg-[#0d9488]" style={{ width: `${rp}%` }} title={labels.r} />
      </div>
      <div
        className={`flex justify-between gap-2 font-semibold ${
          compact ? "text-[10px]" : "text-[11px]"
        }`}
      >
        <span className="text-red-600">
          {labels.l} {Math.round(lp)}%
        </span>
        <span className="text-slate-500">
          {labels.c} {Math.round(cp)}%
        </span>
        <span className="text-teal-700">
          {labels.r} {Math.round(rp)}%
        </span>
      </div>
    </div>
  );
}
