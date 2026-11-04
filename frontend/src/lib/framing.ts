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
  government_critical: "bg-accent",
  government_neutral: "bg-foreground/55",
  government_supportive: "bg-foreground/18",
  insufficient_evidence: "bg-foreground/35",
  analysis_unavailable: "bg-foreground/15",
  unclassified: "bg-foreground/10",
};

export const FRAMING_TEXT: Record<string, string> = {
  government_critical: "text-accent",
  government_neutral: "text-foreground",
  government_supportive: "text-foreground/70",
  insufficient_evidence: "text-foreground/70",
  analysis_unavailable: "text-foreground/50",
  unclassified: "text-foreground/50",
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
  supported: "text-foreground",
  contradicted: "text-accent",
  disputed: "border-b border-foreground text-foreground",
  unverified: "text-foreground/50",
};
