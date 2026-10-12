import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { fetchStoryDetail } from "@/lib/api";
import { formatTimeAgo } from "@/lib/utils";
import { CoverageComparison } from "@/components/CoverageComparison";
import { AnalyzeClaimsButton } from "@/components/AnalyzeClaimsButton";
import { BiasBar } from "@/components/BiasBar";
import { NewsImage } from "@/components/NewsImage";
import { CLAIM_STATUS_COLORS, CLAIM_STATUS_LABELS } from "@/lib/framing";

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
    <div className="space-y-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-foreground/55 hover:text-teal-800"
      >
        <ArrowLeft size={15} /> Feed
      </Link>

      <header className="overflow-hidden rounded-2xl border border-border-subtle bg-white shadow-sm">
        <NewsImage
          src={story.thumbnail_url}
          alt=""
          topic={story.topic}
          priority
          className="aspect-[2/1] w-full sm:aspect-[21/9]"
        />
        <div className="space-y-3 p-5 sm:p-7">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-foreground/50">
            <span className="font-semibold text-teal-800">{story.topic ?? "News"}</span>
            <span>{formatTimeAgo(story.created_at)}</span>
            <span>
              {story.source_count} sources · {story.article_count} articles
            </span>
          </div>
          <h1 className="max-w-3xl font-serif text-2xl font-bold leading-tight sm:text-3xl">
            {story.ai_headline}
          </h1>
          {story.ai_summary && (
            <p className="max-w-2xl text-base leading-relaxed text-foreground/70">{story.ai_summary}</p>
          )}
          <div className="max-w-md space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-foreground/45">
              Government POV across sources
            </p>
            <BiasBar
              left={story.bias_left_pct}
              center={story.bias_center_pct}
              right={story.bias_right_pct}
              critical={story.gov_counts?.critical}
              neutral={story.gov_counts?.neutral}
              supportive={story.gov_counts?.supportive}
            />
          </div>
        </div>
      </header>

      <CoverageComparison articles={story.articles} />

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-serif text-lg font-bold">Headlines</h2>
          <AnalyzeClaimsButton storyId={storyId} />
        </div>
        <div className="overflow-hidden rounded-xl border border-border-subtle bg-white">
          <ul className="divide-y divide-border-subtle">
            {story.headline_comparison.map((row, i) => (
              <li key={`${row.url}-${i}`} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-4">
                <span className="w-36 shrink-0 text-xs font-semibold text-foreground/55">
                  {row.source}
                </span>
                <a
                  href={row.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-sm font-medium hover:text-teal-800"
                >
                  {row.headline}
                </a>
                <span className="text-xs capitalize text-foreground/40">{row.bias ?? "center"}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {story.claims.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-serif text-lg font-bold">Claims</h2>
          <ul className="space-y-2">
            {story.claims.map((claim) => (
              <li key={claim.id} className="rounded-xl border border-border-subtle bg-white p-4 text-sm">
                <span
                  className={`mb-2 inline-block rounded-full border px-2 py-0.5 text-xs font-bold ${
                    CLAIM_STATUS_COLORS[claim.status] ?? ""
                  }`}
                >
                  {CLAIM_STATUS_LABELS[claim.status] ?? claim.status}
                </span>
                <p>{claim.claim_text}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
