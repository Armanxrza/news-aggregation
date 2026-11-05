import Link from "next/link";
import {
  fetchAnalyticsOverview,
  fetchCoverageDistribution,
  fetchFramingModel,
  fetchStories,
  previewFraming,
} from "@/lib/api";
import { GlobalFramingDistribution } from "@/components/GlobalFramingDistribution";
import { FramingPreviewForm } from "@/components/FramingPreview";

export default async function BiasExplorerPage({
  searchParams,
}: {
  searchParams: Promise<{ passage?: string }>;
}) {
  const { passage: rawPassage } = await searchParams;
  const passage = (rawPassage || "").trim();
  let lookup: Awaited<ReturnType<typeof previewFraming>> | null = null;
  let lookupError: string | null = null;
  if (passage.length >= 12) {
    try {
      lookup = await previewFraming(passage.slice(0, 4000));
    } catch (err) {
      lookupError = err instanceof Error ? err.message : "Could not check that passage.";
    }
  } else if (passage.length > 0) {
    lookupError = "Enter at least a short sentence.";
  }

  let distribution: Awaited<ReturnType<typeof fetchCoverageDistribution>> | null = null;
  let analytics: Awaited<ReturnType<typeof fetchAnalyticsOverview>> | null = null;
  let sampleStories: Awaited<ReturnType<typeof fetchStories>>["items"] = [];
  let error = false;
  let modelNote: string | null = null;

  try {
    const [dist, overview, storiesPage, modelInfo] = await Promise.all([
      fetchCoverageDistribution(),
      fetchAnalyticsOverview(),
      fetchStories({ limit: 8, min_sources: 2 }),
      fetchFramingModel().catch(() => null),
    ]);
    if (modelInfo?.metrics?.holdout_macro_f1 != null) {
      const f1 = Math.round(modelInfo.metrics.holdout_macro_f1 * 100);
      const acc = Math.round((modelInfo.metrics.holdout_accuracy ?? 0) * 100);
      modelNote = `${modelInfo.model} · cross-validated accuracy ${acc}% · macro F1 ${f1}% on ${modelInfo.metrics.rows ?? "the"} curated labels`;
    } else if (modelInfo) {
      modelNote = modelInfo.model;
    }
    distribution = dist;
    analytics = overview;
    sampleStories = storiesPage.items;
  } catch {
    error = true;
  }

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="font-serif text-3xl font-semibold">Framing</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-foreground/70">
          Government framing is a three-way division — critical, neutral, or supportive — from a
          desk text classifier blended with quoted wording. It does not understand every article,
          and it is not a Nepal-wide trained political oracle.
        </p>
        {modelNote && <p className="text-xs uppercase tracking-wide text-foreground/50">{modelNote}</p>}
      </header>

      <FramingPreviewForm passage={passage} result={lookup} error={lookupError} />

      {error ? (
        <p className="text-sm text-accent">Could not load framing data.</p>
      ) : (
        <>
          <section className="space-y-3 border border-border bg-surface p-5 text-sm leading-relaxed text-foreground/75">
            <h2 className="font-serif text-lg font-semibold text-foreground">Methodology</h2>
            <ol className="list-decimal space-y-2 pl-5">
              <li>
                Outlets stay on one story only when the headlines are the same event. A different
                event is left out. If fewer than two outlets remain, the page does not draw a bias bar.
              </li>
              <li>
                Government framing is a three-way division (critical, neutral, supportive). A desk
                text classifier is blended with quoted wording from the article. When the text is
                too thin, the article stays unclassified or is marked insufficient evidence.
              </li>
              <li>
                Registry perspective labels default to &ldquo;not independently rated.&rdquo;
              </li>
              <li>
                A coverage gap means an outlet in the registry has no article in that cluster. It
                is not proof the outlet omitted the story.
              </li>
            </ol>
          </section>

          {distribution && <GlobalFramingDistribution distribution={distribution} />}

          {analytics && (
            <section className="border border-border bg-surface p-5">
              <h2 className="font-serif text-lg font-semibold">Corpus snapshot</h2>
              <p className="mt-2 text-sm text-foreground/65">
                {analytics.sources_active} active publishers indexed · framing counts reflect{" "}
                {Object.values(analytics.framing).reduce((a, b) => a + b, 0)} labeled article
                buckets (some articles may appear in aggregate totals).
              </p>
            </section>
          )}

          <section className="space-y-3">
            <h2 className="font-serif text-lg font-semibold">Explore stories</h2>
            <ul className="space-y-2">
              {sampleStories.map((s) => (
                <li key={s.id} className="flex flex-wrap items-baseline gap-2 text-sm">
                  <Link
                    href={`/story/${s.id}`}
                    className="font-semibold underline decoration-foreground/25 underline-offset-2 hover:decoration-foreground"
                  >
                    {s.ai_headline}
                  </Link>
                  <span className="text-xs text-foreground/50">
                    {s.source_count} sources
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
