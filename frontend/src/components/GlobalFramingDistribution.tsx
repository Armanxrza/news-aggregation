import type { CoverageDistributionDTO, FramingCounts } from "@/lib/api";
import { FRAMING_LABELS, FRAMING_TEXT } from "@/lib/framing";
import { FramingBar } from "@/components/FramingBar";

function normalizeCounts(counts: CoverageDistributionDTO["counts"]): FramingCounts {
  return {
    government_critical: counts.government_critical ?? 0,
    government_neutral: counts.government_neutral ?? 0,
    government_supportive: counts.government_supportive ?? 0,
    insufficient_evidence: counts.insufficient_evidence ?? 0,
    analysis_unavailable: counts.analysis_unavailable ?? 0,
    unclassified: counts.unclassified ?? 0,
  };
}

export function GlobalFramingDistribution({
  distribution,
}: {
  distribution: CoverageDistributionDTO;
}) {
  const counts = normalizeCounts(distribution.counts);
  const total = distribution.total_articles || 0;

  return (
    <section className="card p-5" aria-labelledby="distribution-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="distribution-heading" className="font-serif text-lg font-bold">
          Corpus framing distribution
        </h2>
        <span className="text-xs text-foreground/55">
          {distribution.classified_articles} classified of {total} articles
        </span>
      </div>
      <FramingBar counts={counts} total={total} className="mt-4" height="h-5" />
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-foreground/65">
        {(Object.keys(FRAMING_LABELS) as (keyof FramingCounts)[]).map((key) => (
          <li key={key}>
            <span className={FRAMING_TEXT[key]}>{FRAMING_LABELS[key]}</span>{" "}
            <span className="font-semibold text-foreground">{counts[key]}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-foreground/50">
        Published today: {distribution.today_articles}. Latest timestamp:{" "}
        {distribution.latest_published_at
          ? new Date(distribution.latest_published_at).toLocaleString()
          : "—"}
      </p>
    </section>
  );
}
