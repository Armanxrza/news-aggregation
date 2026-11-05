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
