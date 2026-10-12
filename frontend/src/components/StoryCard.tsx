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

const POV_STYLE: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  neutral: "bg-slate-100 text-slate-600",
  supportive: "bg-teal-100 text-teal-800",
};

export function StoryCard({
  story,
  featured = false,
}: {
  story: StoryCardData;
  featured?: boolean;
}) {
  // Prefer soft percentage mix (varies per story); fall back to hard counts
  const critical = story.bias_left_pct ?? story.gov_counts?.critical ?? 0;
  const neutral = story.bias_center_pct ?? story.gov_counts?.neutral ?? 0;
  const supportive = story.bias_right_pct ?? story.gov_counts?.supportive ?? 0;

  if (featured) {
    return (
      <Link
        href={`/story/${story.id}`}
        className="group relative block overflow-hidden rounded-2xl bg-slate-900 shadow-sm"
      >
        <NewsImage
          src={story.thumbnail_url}
          alt=""
          topic={story.topic}
          priority
          className="aspect-[16/9] w-full sm:aspect-[21/9]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 space-y-2.5 p-5 sm:p-7">
          <div className="flex flex-wrap items-center gap-2 text-xs text-white/75">
            <span className="rounded bg-white/15 px-2 py-0.5 font-medium backdrop-blur-sm">
              {story.topic ?? "News"}
            </span>
            <span>{story.source_count} sources</span>
            <span>{formatTimeAgo(story.created_at)}</span>
            <span className="rounded bg-teal-500/30 px-2 py-0.5 font-semibold text-teal-100">
              Gov POV
            </span>
          </div>
          <h2 className="max-w-3xl font-serif text-2xl font-bold leading-tight text-white sm:text-3xl">
            {story.ai_headline}
          </h2>
          <BiasBar
            className="max-w-md [&_span]:!text-white/85"
            left={critical}
            center={neutral}
            right={supportive}
          />
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/story/${story.id}`}
      className="group flex overflow-hidden rounded-xl border border-border-subtle bg-white shadow-[0_1px_0_rgba(15,23,42,0.04)] transition hover:border-border hover:shadow-md"
    >
      <NewsImage
        src={story.thumbnail_url}
        alt=""
        topic={story.topic}
        className="min-h-[128px] w-[36%] min-w-[118px] max-w-[210px] shrink-0 self-stretch sm:min-h-[140px] sm:w-48"
      />
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5 p-3.5 sm:p-4">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-foreground/50">
          <span className="font-semibold text-teal-800">{story.topic ?? "News"}</span>
          <span>·</span>
          <span>{story.source_count} sources</span>
          <span>·</span>
          <span>{formatTimeAgo(story.created_at)}</span>
        </div>
        <h2 className="font-serif text-base font-bold leading-snug text-foreground group-hover:text-teal-900 sm:text-lg">
          {story.ai_headline}
        </h2>
        {story.source_bias && story.source_bias.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {story.source_bias.slice(0, 4).map((s) => (
              <span
                key={s.source}
                className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${POV_STYLE[s.pov] || POV_STYLE.neutral}`}
              >
                {s.source.split(" ")[0]} · C{s.scores?.critical ?? "?"}%/S{s.scores?.supportive ?? "?"}%
              </span>
            ))}
          </div>
        )}
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
