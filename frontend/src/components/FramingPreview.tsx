import Link from "next/link";
import type { FramingPreview } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";
import { framingLabel } from "@/lib/framing";

const SAMPLES = [
  "Nepal Rastra Bank keeps policy rate unchanged at 6.5 percent",
  "CIAA widens probe into the cabinet road contract",
  "टेक्सासमा डेमोक्रेटहरूको अप्रत्याशित जितपछि इलोन मस्कको साम्राज्यमा धक्का",
];

export function FramingPreviewForm({
  passage,
  result,
  error,
}: {
  passage: string;
  result: FramingPreview | null;
  error: string | null;
}) {
  return (
    <form action="/bias" method="get" className="space-y-4 border border-border bg-surface p-5">
      <div className="space-y-1">
        <h2 className="font-serif text-lg font-semibold">Score a passage</h2>
        <p className="text-sm text-foreground/65">
          Paste a headline or a news link. The desk looks it up in the stories it already holds.
          A match shows that story&apos;s rating. Anything else asks for the link.
        </p>
      </div>
      <label className="block text-xs font-semibold uppercase tracking-wide text-foreground/55" htmlFor="passage">
        Passage or link
      </label>
      <textarea
        id="passage"
        name="passage"
        defaultValue={passage}
        rows={4}
        required
        minLength={12}
        placeholder="Paste a headline or a news link"
        className="w-full border border-border bg-background px-3 py-2 text-sm leading-relaxed outline-none"
      />
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((sample) => (
          <a
            key={sample}
            href={`/bias?passage=${encodeURIComponent(sample)}`}
            className="border border-foreground/20 px-2 py-1 text-left text-xs text-foreground/70 hover:border-foreground"
          >
            {sample.slice(0, 42)}
            {sample.length > 42 ? "…" : ""}
          </a>
        ))}
      </div>
      <button
        type="submit"
        className="border border-accent bg-accent px-4 py-2 text-sm font-semibold text-background"
      >
        Check this news
      </button>
      {error && <p className="text-sm text-accent">{error}</p>}
      {result && (
        <div className="space-y-3 border-t border-border pt-4">
          <p className="text-sm leading-relaxed">{result.message}</p>
          {result.found && result.headline && (
            <p className="font-serif text-lg font-semibold leading-snug">{result.headline}</p>
          )}
          {result.found && result.sources.length > 0 && (
            <p className="text-xs text-foreground/60">{result.sources.join(" · ")}</p>
          )}
          {result.found && result.coverage_sufficient && result.scores && (
            <div className="max-w-md space-y-2">
              {result.label && <p className="text-sm font-semibold">{framingLabel(result.label)}</p>}
              <BiasBar
                left={result.scores.critical}
                center={result.scores.neutral}
                right={result.scores.supportive}
              />
            </div>
          )}
          {result.found && result.story_id != null && (
            <Link
              href={`/story/${result.story_id}`}
              className="inline-block text-sm underline decoration-foreground/30 underline-offset-2"
            >
              Open the story
            </Link>
          )}
        </div>
      )}
    </form>
  );
}
