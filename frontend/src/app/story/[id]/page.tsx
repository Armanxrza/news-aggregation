import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchStoryDetail } from "@/lib/api";
import { formatTimeAgo } from "@/lib/utils";
import { CoverageComparison } from "@/components/CoverageComparison";
import { AnalyzeClaimsButton } from "@/components/AnalyzeClaimsButton";
import { BiasBar } from "@/components/BiasBar";
import { NewsImage } from "@/components/NewsImage";
import { CLAIM_STATUS_COLORS, CLAIM_STATUS_LABELS, framingLabel } from "@/lib/framing";

const POLITICAL_AXIS = new Set(["left", "center", "centre", "right"]);

function headlineFraming(framing: string | null, bias?: string | null) {
  if (framing && !POLITICAL_AXIS.has(framing)) return framingLabel(framing);
  if (bias && !POLITICAL_AXIS.has(bias)) return framingLabel(bias);
  return "Unclassified";
}

export default async function StoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const storyId = Number(id);
  if (!Number.isInteger(storyId)) notFound();

  let story;
  try {
    story = await fetchStoryDetail(storyId);
  } catch {
    notFound();
  }
  const eventIdentity = story.event_identity;
  const identityFields = [
    ["Action", eventIdentity?.action],
    ["People and institutions", eventIdentity?.actors?.join(", ")],
    ["Location", eventIdentity?.locations?.join(", ")],
    ["Event subject", eventIdentity?.objects?.join(", ")],
    ["Time marker", eventIdentity?.time_markers?.join(", ")],
  ].filter(([, value]) => Boolean(value));

  return (
    <div className="space-y-10">
      <Link href="/" className="text-sm text-foreground/60 hover:text-foreground">
        ← Feed
      </Link>

      <header className="space-y-4 border-b border-foreground/20 pb-8">
        {story.thumbnail_url && (
          <NewsImage
            src={story.thumbnail_url}
            alt=""
            topic={story.topic}
            priority
            className="aspect-[2/1] w-full border border-border sm:aspect-[21/9]"
          />
        )}
        <div className="space-y-3">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs uppercase tracking-wide text-foreground/50">
            <span>{story.topic ?? "News"}</span>
            <span className="normal-case tracking-normal">{formatTimeAgo(story.created_at)}</span>
            <span className="normal-case tracking-normal">
              {story.source_count} sources · {story.article_count} articles
            </span>
          </div>
          <h1 className="max-w-3xl font-serif text-3xl font-semibold leading-tight sm:text-4xl">
            {story.ai_headline}
          </h1>
          {story.ai_summary && (
            <p className="max-w-2xl text-base leading-relaxed text-foreground/75">{story.ai_summary}</p>
          )}
          <div className="flex flex-wrap items-center gap-2 text-xs text-foreground/55">
            <span className="border border-foreground/15 px-2.5 py-1 font-semibold">
              Relevance {story.importance_score ?? "—"}/100
            </span>
            <span>{story.source_diversity?.independent_sources ?? story.source_count} independent sources</span>
            {(story.source_diversity?.syndicated_articles ?? 0) > 0 && (
              <span>{story.source_diversity?.syndicated_articles} syndicated copies identified</span>
            )}
          </div>
          {identityFields.length > 0 && (
            <div className="grid gap-2 border border-border bg-surface p-4 sm:grid-cols-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-foreground/50 sm:col-span-2">
                Event identity · {story.cluster_relationship?.replace(/_/g, " ") ?? "new story"}
              </p>
              {identityFields.map(([label, value]) => (
                <p key={label} className="text-sm text-foreground/75">
                  <span className="mr-1 font-semibold text-foreground/50">{label}:</span>{value}
                </p>
              ))}
              {story.cluster_evidence?.evidence?.length ? (
                <ul className="list-inside list-disc text-xs text-foreground/55 sm:col-span-2">
                  {story.cluster_evidence.evidence.map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : null}
            </div>
          )}
          <div className="max-w-md space-y-1.5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-foreground/50">
              Government framing
            </p>
            {story.coverage_sufficient === false ? (
              <p className="text-sm text-foreground/70">
                {story.bias_note || "Not enough related coverage to show bias."}
              </p>
            ) : (
              <BiasBar
                left={story.bias_left_pct}
                center={story.bias_center_pct}
                right={story.bias_right_pct}
                critical={story.gov_counts?.critical}
                neutral={story.gov_counts?.neutral}
                supportive={story.gov_counts?.supportive}
              />
            )}
            {(story.omitted_unrelated ?? 0) > 0 && (
              <p className="text-xs text-foreground/55">
                {story.omitted_unrelated} unrelated {story.omitted_unrelated === 1 ? "headline was" : "headlines were"} left
                out of this coverage.
              </p>
            )}
          </div>
        </div>
      </header>

      <CoverageComparison
        articles={story.articles}
        coverageSufficient={story.coverage_sufficient !== false}
        biasNote={story.bias_note}
      />

      {story.timeline.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Story timeline</h2>
          <ol className="space-y-2 border-l-2 border-foreground/15 pl-4">
            {story.timeline.map((item, index) => (
              <li key={`${item.url}-${index}`} className="relative border border-border bg-surface p-3">
                <span className="absolute -left-[21px] top-4 h-2.5 w-2.5 bg-foreground ring-4 ring-background" />
                <div className="flex flex-wrap gap-x-2 text-[11px] text-foreground/45">
                  <span className="font-semibold text-foreground/75">{item.source}</span>
                  <span>{item.published_at ? formatTimeAgo(item.published_at) : "Time unavailable"}</span>
                  {item.is_syndicated_duplicate && <span>Syndicated copy</span>}
                </div>
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="mt-1 block text-sm font-medium hover:underline">
                  {item.headline}
                </a>
              </li>
            ))}
          </ol>
        </section>
      )}

      {story.related_stories && story.related_stories.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Related events</h2>
          <ul className="space-y-2">
            {story.related_stories.map((related) => (
              <li key={related.id}>
                <Link className="text-sm font-medium underline decoration-transparent underline-offset-2 hover:decoration-foreground/40" href={`/story/${related.id}`}>
                  {related.ai_headline}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-serif text-xl font-semibold">Headlines</h2>
          <AnalyzeClaimsButton storyId={storyId} />
        </div>
        <div className="border border-border bg-surface">
          <ul className="divide-y divide-border">
            {story.headline_comparison.map((row, i) => (
              <li key={`${row.url}-${i}`} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-4">
                <span className="w-36 shrink-0 text-xs font-semibold text-foreground/55">
                  {row.source}
                </span>
                <a
                  href={row.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-sm font-medium underline decoration-transparent underline-offset-2 hover:decoration-foreground/40"
                >
                  {row.headline}
                </a>
                <span className="text-xs text-foreground/50">
                  {headlineFraming(row.framing, row.bias)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {story.claims.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Claims</h2>
          <ul className="border-t border-border">
            {story.claims.map((claim) => (
              <li key={claim.id} className="border-b border-border py-3 text-sm">
                <span
                  className={`inline-block text-xs font-semibold uppercase tracking-wide ${
                    CLAIM_STATUS_COLORS[claim.status] ?? "text-foreground"
                  }`}
                >
                  {CLAIM_STATUS_LABELS[claim.status] ?? claim.status}
                </span>
                <p className="mt-1">{claim.claim_text}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
