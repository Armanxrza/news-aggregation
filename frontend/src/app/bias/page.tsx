import Link from "next/link";
import {
  fetchAnalyticsOverview,
  fetchCoverageDistribution,
  fetchStories,
  fetchStoryDetail,
} from "@/lib/api";
import { GlobalFramingDistribution } from "@/components/GlobalFramingDistribution";

export default async function BiasExplorerPage() {
  let distribution: Awaited<ReturnType<typeof fetchCoverageDistribution>> | null = null;
  let analytics: Awaited<ReturnType<typeof fetchAnalyticsOverview>> | null = null;
  let sampleStories: Awaited<ReturnType<typeof fetchStories>>["items"] = [];
  let error = false;

  try {
    const [dist, overview, storiesPage] = await Promise.all([
      fetchCoverageDistribution(),
      fetchAnalyticsOverview(),
      fetchStories({ limit: 8, min_sources: 2 }),
    ]);
    distribution = dist;
    analytics = overview;
    sampleStories = storiesPage.items;
  } catch {
    error = true;
  }

  const signalSamples: { headline: string; source: string; signals: Record<string, unknown> }[] =
    [];

  for (const story of sampleStories) {
    try {
      const detail = await fetchStoryDetail(story.id);
      for (const article of detail.articles) {
        if (article.signals && Object.keys(article.signals).length > 0) {
          signalSamples.push({
            headline: article.original_headline,
            source: article.source_name,
            signals: article.signals,
          });
          if (signalSamples.length >= 12) break;
        }
      }
      if (signalSamples.length >= 12) break;
    } catch {
      /* skip */
    }
  }

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="font-serif text-3xl font-bold">Bias explorer</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-foreground/65">
          SajhaNews does <strong className="font-semibold text-foreground">not</strong> assign
          left–right publisher scores. Instead we report (1) government framing on each article,
          (2) optional loaded-language signals when the model extracts them, and (3) registry
          perspective labels that default to &ldquo;not independently rated.&rdquo;
        </p>
      </header>

      {error ? (
        <p className="card p-6 text-sm text-red-700">Could not load bias explorer data.</p>
      ) : (
        <>
          <section className="card space-y-3 p-6 text-sm leading-relaxed text-foreground/70">
            <h2 className="font-serif text-lg font-bold text-foreground">Methodology</h2>
            <ol className="list-decimal space-y-2 pl-5">
              <li>
                Articles are clustered into stories by headline similarity — see cluster method on
                each story page.
              </li>
              <li>
                Government framing classifies tone toward the Nepali government (critical, neutral,
                supportive, or insufficient evidence).
              </li>
              <li>
                Ideological bias bars (left/center/right) are deliberately disabled — we do not
                show percentages without a documented, independent rating source.
              </li>
              <li>
                Coverage gaps list outlets in our registry without an article in a cluster; this is
                not proof of editorial omission.
              </li>
            </ol>
          </section>

          {distribution && <GlobalFramingDistribution distribution={distribution} />}

          {analytics && (
            <section className="card p-5">
              <h2 className="font-serif text-lg font-bold">Corpus snapshot</h2>
              <p className="mt-2 text-sm text-foreground/60">
                {analytics.sources_active} active publishers indexed · framing counts reflect{" "}
                {Object.values(analytics.framing).reduce((a, b) => a + b, 0)} labeled article
                buckets (some articles may appear in aggregate totals).
              </p>
            </section>
          )}

          <section className="space-y-4">
            <h2 className="font-serif text-lg font-bold">Loaded-language signals (samples)</h2>
            <p className="text-sm text-foreground/55">
              Pulled from real article <code className="text-xs">signals</code> JSON when present —
              not invented scores.
            </p>
            {signalSamples.length === 0 ? (
              <p className="text-sm text-foreground/50">
                No signal payloads in recent multi-source stories yet. Run framing analysis from
                Admin after crawl.
              </p>
            ) : (
              <ul className="grid gap-3 lg:grid-cols-2">
                {signalSamples.map((s, i) => (
                  <li key={`${s.source}-${i}`} className="card p-4 text-sm">
                    <p className="text-xs font-bold text-teal-800">{s.source}</p>
                    <p className="mt-1 font-medium leading-snug">{s.headline}</p>
                    <pre className="mt-2 max-h-32 overflow-auto rounded bg-surface-hover p-2 text-[11px] text-foreground/55">
                      {JSON.stringify(s.signals, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="font-serif text-lg font-bold">Explore stories</h2>
            <ul className="space-y-2">
              {sampleStories.map((s) => (
                <li key={s.id} className="flex flex-wrap items-baseline gap-2 text-sm">
                  <Link href={`/story/${s.id}`} className="font-semibold text-teal-800 hover:underline">
                    {s.ai_headline}
                  </Link>
                  <span className="text-xs text-foreground/45">
                    {s.source_count} sources · dominant framing from article counts
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
