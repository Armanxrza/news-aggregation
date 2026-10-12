import type { FramingCounts } from "@/lib/api";

export const FRAMING_LABELS: Record<string, string> = {
  government_critical: "Critical of government",
  government_neutral: "Neutral",
  government_supportive: "Supportive of government",
  insufficient_evidence: "Insufficient evidence",
  analysis_unavailable: "Analysis unavailable",
  unclassified: "Unclassified",
};

export const FRAMING_COLORS: Record<string, string> = {
  government_critical: "bg-red-600",
  government_neutral: "bg-slate-400",
  government_supportive: "bg-teal-600",
  insufficient_evidence: "bg-amber-400",
  analysis_unavailable: "bg-orange-300",
  unclassified: "bg-slate-200",
};

export const FRAMING_TEXT: Record<string, string> = {
  government_critical: "text-red-700",
  government_neutral: "text-slate-600",
  government_supportive: "text-teal-700",
  insufficient_evidence: "text-amber-700",
  analysis_unavailable: "text-orange-600",
  unclassified: "text-slate-500",
};

export function framingLabel(value: string | null | undefined): string {
  if (!value) return "Unclassified";
  return FRAMING_LABELS[value] ?? value.replace(/_/g, " ");
}

export function classifiedTotal(counts: Partial<FramingCounts>): number {
  return (
    (counts.government_critical ?? 0) +
    (counts.government_neutral ?? 0) +
    (counts.government_supportive ?? 0)
  );
}

export function perspectiveLabel(value: string | null | undefined): string {
  if (!value || value === "not_independently_rated") {
    return "Not independently rated";
  }
  return value.replace(/_/g, " ");
}

export const CLAIM_STATUS_LABELS: Record<string, string> = {
  supported: "Supported",
  contradicted: "Contradicted",
  disputed: "Disputed",
  unverified: "Unverified",
};

export const CLAIM_STATUS_COLORS: Record<string, string> = {
  supported: "bg-emerald-100 text-emerald-800 border-emerald-200",
  contradicted: "bg-red-100 text-red-800 border-red-200",
  disputed: "bg-amber-100 text-amber-900 border-amber-200",
  unverified: "bg-slate-100 text-slate-700 border-slate-200",
};
