import Link from "next/link";
import { StoryCard, type Story } from "@/components/StoryCard";
import { BiasBar } from "@/components/BiasBar";
import { fetchStories, fetchTopics } from "@/lib/api";
import { formatTimeAgo } from "@/lib/utils";
import {
  TrendingUp, Globe2, MapPin, Sparkles, Filter,
  ShieldAlert, BookOpen, ArrowRight, Flame, Layers, Search
} from "lucide-react";
import { RefreshFeedButton } from "@/components/RefreshFeedButton";

const FALLBACK_THUMBNAIL =
  "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; lang?: string; search?: string }>;
}) {
  const { topic, lang, search } = (await searchParams) ?? {};

  let stories: Story[] = [];
  let topicsList: { topic: string; count: number }[] = [];
  let fetchError = false;

  try {
    const [data, topics] = await Promise.all([
      fetchStories({ topic, lang, search }),
      fetchTopics(),
    ]);

    topicsList = topics;

    stories = data.map((d) => ({
      id: String(d.id),
      headline: d.ai_headline,
      thumbnail_url: d.thumbnail_url,
      source_count: d.source_count,
      sources: d.sources,
      languages: d.languages,
      bias: { left: d.bias_left_pct, center: d.bias_center_pct, right: d.bias_right_pct },
      time_ago: formatTimeAgo(d.created_at),
      topic: d.topic ?? "General",
    }));
  } catch (error) {
    console.error("Failed to fetch stories:", error);
    fetchError = true;
  }

  // Identify Hero Story (most covered or first story)
  const heroStory = stories.length > 0 ? stories[0] : null;
  const gridStories = stories.length > 1 ? stories.slice(1) : [];

  // Blindspot count
  const blindspotStories = stories.filter(
    (s) => s.bias.left >= 55 || s.bias.right >= 55
  );

  const activeTopic = topic || "All";
  const activeLang = lang || "All";

  // Predefined topic list merged with fetched topics
  const commonTopics = ["All", "Nepal", "Politics", "Business", "Sports", "World"];

  return (
    <div className="space-y-8 py-8">
      {/* Ground News Top Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-border">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
            Nepal & World News Coverage
          </h1>
          <p className="text-foreground/60 text-sm mt-1">
            Compare reporting from across the political spectrum and spot media blindspots.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <RefreshFeedButton />
        </div>
      </div>

      {/* Filter and Topic Tabs Bar */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          {/* Topic Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full no-scrollbar">
            {commonTopics.map((t) => {
              const isActive = activeTopic.toLowerCase() === t.toLowerCase();
              return (
                <Link
                  key={t}
                  href={`/?${new URLSearchParams({
                    ...(t !== "All" ? { topic: t } : {}),
                    ...(activeLang !== "All" ? { lang: activeLang } : {}),
                    ...(search ? { search } : {}),
                  }).toString()}`}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap ${
                    isActive
                      ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                      : "bg-surface hover:bg-surface-hover text-foreground/70 border border-border"
                  }`}
                >
                  {t}
                </Link>
              );
            })}
          </div>

          {/* Language Toggle */}
          <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-border shrink-0">
            <Link
              href={`/?${new URLSearchParams({
                ...(activeTopic !== "All" ? { topic: activeTopic } : {}),
                ...(search ? { search } : {}),
              }).toString()}`}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                activeLang === "All"
                  ? "bg-background text-foreground shadow-sm font-bold"
                  : "text-foreground/60 hover:text-foreground"
              }`}
            >
              All Languages
            </Link>
            <Link
              href={`/?${new URLSearchParams({
                ...(activeTopic !== "All" ? { topic: activeTopic } : {}),
                lang: "ne",
                ...(search ? { search } : {}),
              }).toString()}`}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                activeLang === "ne"
                  ? "bg-red-600/90 text-white font-bold"
                  : "text-foreground/60 hover:text-foreground"
              }`}
            >
              🇳🇵 नेपाली
            </Link>
            <Link
              href={`/?${new URLSearchParams({
                ...(activeTopic !== "All" ? { topic: activeTopic } : {}),
                lang: "en",
                ...(search ? { search } : {}),
              }).toString()}`}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                activeLang === "en"
                  ? "bg-blue-600 text-white font-bold"
                  : "text-foreground/60 hover:text-foreground"
              }`}
            >
              English
            </Link>
          </div>
        </div>
      </div>

      {/* Blindspot Alert Banner (if blindspots detected) */}
      {blindspotStories.length > 0 && (
        <div className="bg-gradient-to-r from-blue-950/40 via-slate-900/60 to-red-950/40 border border-border/80 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <ShieldAlert size={20} />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">
                {blindspotStories.length} Media Blindspot{blindspotStories.length > 1 ? "s" : ""} Identified Today
              </p>
              <p className="text-xs text-foreground/60">
                Stories predominantly covered by only one side of the political spectrum.
              </p>
            </div>
          </div>
          <Link
            href={`/story/${blindspotStories[0].id}`}
            className="text-xs font-bold text-blue-400 hover:text-blue-300 flex items-center gap-1 bg-surface/80 px-3 py-2 rounded-lg border border-border shrink-0 transition-colors"
          >
            Inspect Top Blindspot <ArrowRight size={13} />
          </Link>
        </div>
      )}

      {/* Hero Featured Story (Ground News Signature Section) */}
      {heroStory && (
        <section className="relative overflow-hidden rounded-3xl border border-border bg-surface shadow-2xl transition-all">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-0">
            {/* Hero Image */}
            <div className="relative lg:col-span-7 h-72 sm:h-96 lg:h-auto overflow-hidden bg-slate-950">
              <img
                src={heroStory.thumbnail_url ?? FALLBACK_THUMBNAIL}
                alt={heroStory.headline}
                className="w-full h-full object-cover opacity-90 hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface via-black/20 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-surface" />

              {/* Topic & Nepal badge */}
              <div className="absolute top-4 left-4 flex items-center gap-2">
                <span className="bg-blue-600 text-white font-black text-xs px-3 py-1 rounded-full uppercase tracking-wider shadow-lg">
                  ★ Featured Story
                </span>
                <span className="bg-background/80 backdrop-blur-md text-foreground font-bold text-xs px-3 py-1 rounded-full uppercase tracking-wider border border-border">
                  {heroStory.topic}
                </span>
                {heroStory.languages.includes("ne") && (
                  <span className="bg-red-600/90 text-white font-bold text-xs px-2.5 py-1 rounded-full">
                    🇳🇵 नेपाली
                  </span>
                )}
              </div>
            </div>

            {/* Hero Details */}
            <div className="lg:col-span-5 p-6 sm:p-8 flex flex-col justify-between gap-6 bg-surface">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground/50">
                  <BookOpen size={14} className="text-blue-400" />
                  <span>{heroStory.source_count} Independent Sources Reporting</span>
                  <span>•</span>
                  <span>Fetched {heroStory.time_ago}</span>
                </div>

                <Link href={`/story/${heroStory.id}`}>
                  <h2 className="text-2xl sm:text-3xl font-extrabold leading-tight text-foreground hover:text-blue-400 transition-colors">
                    {heroStory.headline}
                  </h2>
                </Link>

                {/* Sources list */}
                {heroStory.sources.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {heroStory.sources.slice(0, 5).map((src) => (
                      <span
                        key={src}
                        className="text-xs font-medium px-2.5 py-1 rounded-md bg-surface-hover text-foreground/80 border border-border"
                      >
                        {src}
                      </span>
                    ))}
                    {heroStory.sources.length > 5 && (
                      <span className="text-xs font-medium px-2 py-1 rounded-md bg-surface-muted text-foreground/50">
                        +{heroStory.sources.length - 5} more
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Ground News Bias Meter */}
              <div className="bg-background/80 rounded-2xl p-5 border border-border/80 space-y-3">
                <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                  <span className="text-blue-400">Left {Math.round(heroStory.bias.left)}%</span>
                  <span className="text-slate-400">Center {Math.round(heroStory.bias.center)}%</span>
                  <span className="text-red-400">Right {Math.round(heroStory.bias.right)}%</span>
                </div>

                <BiasBar
                  left={heroStory.bias.left}
                  center={heroStory.bias.center}
                  right={heroStory.bias.right}
                  className="h-2.5"
                />

                <p className="text-[11px] text-foreground/50 leading-relaxed">
                  Media distribution across {heroStory.source_count} publishers reporting on this development.
                </p>
              </div>

              <Link
                href={`/story/${heroStory.id}`}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
              >
                <span>Compare {heroStory.source_count} Coverage Perspectives</span>
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* Grid of Remaining Stories */}
      {fetchError ? (
        <div className="text-center py-20 bg-surface rounded-2xl border border-border p-8">
          <p className="text-foreground/70 font-semibold mb-2">Could not reach the SajhaNews backend API.</p>
          <p className="text-foreground/50 text-xs mb-4">Verify backend availability at:</p>
          <code className="text-xs bg-background border border-border px-3 py-1.5 rounded-md text-blue-400 inline-block">
            https://api.sajhanews.yagyatech.com.np/api/stories
          </code>
        </div>
      ) : gridStories.length > 0 ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-foreground">Latest Head-to-Head Coverage</h3>
            <span className="text-xs text-foreground/50 font-medium">{stories.length} stories available</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {gridStories.map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </div>
        </section>
      ) : stories.length === 1 ? (
        // Only 1 story exists (shown in hero)
        <div className="text-center py-10 text-foreground/50 text-sm">
          You've caught up with all stories in this section.
        </div>
      ) : (
        <div className="text-center py-20 bg-surface rounded-2xl border border-border p-8 space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center">
            <Layers size={24} />
          </div>
          <h3 className="text-lg font-bold text-foreground">No stories found for this filter</h3>
          <p className="text-foreground/50 text-xs max-w-sm mx-auto">
            Try switching topics or trigger the RSS crawler to fetch new articles from all 30+ portals.
          </p>
          <div className="pt-2">
            <RefreshFeedButton />
          </div>
        </div>
      )}
    </div>
  );
}
