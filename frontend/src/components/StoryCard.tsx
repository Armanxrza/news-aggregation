import Link from "next/link";
import type { StoryDTO } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";
import { NewsImage } from "@/components/NewsImage";
import { formatTimeAgo } from "@/lib/utils";

export type StoryCardData = Pick<
  StoryDTO,
  | "id"
  | "ai_headline"
  | "topic"
  | "created_at"
  | "source_count"
  | "thumbnail_url"
  | "sources"
  | "languages"
  | "bias_left_pct"
  | "bias_center_pct"
  | "bias_right_pct"
  | "gov_counts"
  | "source_bias"
>;

function povClass(pov: string) {
  if (pov === "critical") return "text-accent";
  if (pov === "supportive") return "text-foreground/55";
  return "text-foreground/70";
}

export function StoryCard({
  story,
  featured = false,
}: {
  story: StoryCardData;
  featured?: boolean;
}) {
  const critical = story.bias_left_pct ?? story.gov_counts?.critical ?? 0;
  const neutral = story.bias_center_pct ?? story.gov_counts?.neutral ?? 0;
  const supportive = story.bias_right_pct ?? story.gov_counts?.supportive ?? 0;

  const meta = (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-foreground/50">
      <span>{story.topic ?? "News"}</span>
      <span aria-hidden="true">·</span>
      <span className="normal-case tracking-normal">{story.source_count} sources</span>
      <span aria-hidden="true">·</span>
      <span className="normal-case tracking-normal">{formatTimeAgo(story.created_at)}</span>
    </div>
  );

  const outlets =
    story.source_bias && story.source_bias.length > 0 ? (
      <p className="text-[11px] leading-relaxed text-foreground/60">
        {story.source_bias.slice(0, 4).map((s, index) => (
          <span key={s.source} className={povClass(s.pov)}>
            {index > 0 ? " · " : ""}
            {s.source} C{s.scores?.critical ?? "—"}/S{s.scores?.supportive ?? "—"}
          </span>
        ))}
      </p>
    ) : null;

  const image = story.thumbnail_url ? (
    <NewsImage
      src={story.thumbnail_url}
      alt=""
      topic={story.topic}
      priority={featured}
      className={featured ? "aspect-[3/2] w-full" : "aspect-[4/3] w-full"}
    />
  ) : null;

  if (featured) {
    return (
      <Link
        href={`/story/${story.id}`}
        className={
          image
            ? "group grid items-start gap-5 border-b border-foreground/30 pb-6 md:grid-cols-[minmax(0,1.4fr)_minmax(200px,0.85fr)]"
            : "group block border-b border-foreground/30 pb-6"
        }
      >
        <div className="min-w-0 space-y-3">
          {meta}
          <h2 className="max-w-3xl font-serif text-3xl font-semibold leading-[1.15] group-hover:underline group-hover:decoration-foreground/35 group-hover:underline-offset-4 sm:text-4xl">
            {story.ai_headline}
          </h2>
          {outlets}
          <BiasBar left={critical} center={neutral} right={supportive} className="max-w-md" />
        </div>
        {image}
      </Link>
    );
  }

  return (
    <Link
      href={`/story/${story.id}`}
      className={
        image
          ? "group grid grid-cols-[6.5rem_minmax(0,1fr)] items-start gap-4 border-b border-foreground/15 py-4 sm:grid-cols-[8.75rem_minmax(0,1fr)]"
          : "group block border-b border-foreground/15 py-4"
      }
    >
      {image}
      <div className="flex min-w-0 flex-col justify-center gap-1.5">
        {meta}
        <h2 className="font-serif text-lg font-semibold leading-snug group-hover:underline group-hover:decoration-foreground/35 group-hover:underline-offset-2 sm:text-xl">
          {story.ai_headline}
        </h2>
        {outlets}
        <BiasBar
          className="mt-0.5 max-w-sm"
          left={critical}
          center={neutral}
          right={supportive}
          compact
        />
      </div>
    </Link>
  );
}
