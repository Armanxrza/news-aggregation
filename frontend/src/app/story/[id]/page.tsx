import { fetchStoryDetail, type ArticleDTO } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";
import { formatTimeAgo } from "@/lib/utils";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, ExternalLink, Clock, Globe,
  TrendingUp, ChevronRight, BookOpen, ShieldAlert,
  Layers, CheckCircle2, Sparkles
} from "lucide-react";

const FALLBACK_THUMBNAIL =
  "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80";

// ─── Bias helpers ────────────────────────────────────────────────────────────

function biasLabel(b: number | null): string {
  if (b === null) return "Neutral / Center";
  if (b <= -0.4) return "Left";
  if (b < -0.1) return "Center-Left";
  if (b > 0.4) return "Right";
  if (b > 0.1) return "Center-Right";
  return "Center";
}

function biasColor(b: number | null): string {
  if (b === null) return "bg-slate-500/10 text-slate-300 border-slate-500/20";
  if (b <= -0.1) return "bg-blue-500/10 text-blue-400 border-blue-500/20";
  if (b >= 0.1) return "bg-red-500/10 text-red-400 border-red-500/20";
  return "bg-slate-500/10 text-slate-300 border-slate-500/20";
}

// ─── Article Source Card ──────────────────────────────────────────────────────

function ArticleCard({ article }: { article: ArticleDTO }) {
  const timeStr = formatTimeAgo(article.published_at);

  const isNepali = article.source_language === "ne";

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="glass-card rounded-2xl overflow-hidden flex flex-col h-full bg-surface border border-border transition-all duration-300 hover:border-blue-500/40 hover:shadow-xl group"
    >
      {/* Thumbnail */}
      <div className="relative h-44 w-full overflow-hidden shrink-0 bg-slate-900">
        <img
          src={article.thumbnail_url ?? FALLBACK_THUMBNAIL}
          alt={article.original_headline}
          className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105 opacity-90 group-hover:opacity-100"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-black/30 to-transparent" />

        {/* Source badge overlay */}
        <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between gap-2">
          <span className="bg-background/90 backdrop-blur-md text-foreground text-xs font-extrabold px-2.5 py-1 rounded-lg border border-border/80 truncate max-w-[70%]">
            {article.source_name}
          </span>
          {isNepali && (
            <span className="bg-red-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 shrink-0 shadow-sm">
              🇳🇵 नेपाली
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-5 flex flex-col gap-3 flex-1 justify-between">
        <div className="space-y-2.5">
          {/* Bias pill */}
          <div className="flex items-center justify-between gap-2">
            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${biasColor(article.source_bias)}`}>
              {biasLabel(article.source_bias)}
            </span>
            {timeStr && (
              <span className="text-[10px] text-foreground/45 flex items-center gap-1">
                <Clock size={11} /> Fetched {timeStr}
              </span>
            )}
          </div>

          <h3 className="text-sm font-bold leading-snug line-clamp-2 text-foreground group-hover:text-blue-400 transition-colors">
            {article.original_headline}
          </h3>

          {article.snippet && (
            <p className="text-xs text-foreground/60 line-clamp-3 leading-relaxed">
              {article.snippet}…
            </p>
          )}
        </div>

        {/* Read link */}
        <div className="pt-3 border-t border-border/60 flex items-center justify-between text-xs font-semibold text-blue-400">
          <span className="flex items-center gap-1.5 text-foreground/60">
            <Globe size={13} className="text-blue-400" />
            <span className="truncate max-w-[140px]">{article.source_domain}</span>
          </span>
          <span className="flex items-center gap-1 group-hover:underline">
            Read Source <ExternalLink size={12} />
          </span>
        </div>
      </div>
    </a>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function StoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let story;
  try {
    story = await fetchStoryDetail(Number(id));
  } catch (err) {
    console.error("fetchStoryDetail failed with error:", err);
    notFound();
  }

  const publishedDate = new Date(story.created_at).toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const totalBias = story.bias_left_pct + story.bias_center_pct + story.bias_right_pct;

  // Blindspot logic
  const isLeftBlindspot = story.bias_left_pct >= 55;
  const isRightBlindspot = story.bias_right_pct >= 55;

  // Group articles by lean
  const leftArticles = story.articles.filter((a) => (a.source_bias ?? 0) < -0.1);
  const rightArticles = story.articles.filter((a) => (a.source_bias ?? 0) > 0.1);
  const centerArticles = story.articles.filter(
    (a) => (a.source_bias ?? 0) >= -0.1 && (a.source_bias ?? 0) <= 0.1
  );

  return (
    <div className="py-8 space-y-8">
      {/* Back navigation breadcrumb */}
      <div className="flex items-center justify-between text-sm text-foreground/50 pb-2">
        <Link href="/" className="hover:text-blue-400 transition-colors flex items-center gap-1.5 font-semibold">
          <ArrowLeft size={16} /> Back to Live Feed
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-surface px-2.5 py-1 rounded-md border border-border text-foreground/70">
            {story.topic}
          </span>
          <span className="text-xs text-foreground/40">• Story #{story.id}</span>
        </div>
      </div>

      {/* Hero Header */}
      <div className="relative w-full rounded-3xl overflow-hidden shadow-2xl bg-slate-950" style={{ minHeight: "380px" }}>
        <img
          src={story.thumbnail_url ?? FALLBACK_THUMBNAIL}
          alt={story.ai_headline}
          className="absolute inset-0 w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-black/60 to-transparent" />

        {/* Content over image */}
        <div className="relative p-6 sm:p-10 flex flex-col justify-end min-h-[380px] gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="bg-blue-600 text-white text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider shadow-md">
              {story.topic}
            </span>
            {story.languages.includes("ne") && (
              <span className="bg-red-600/90 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-md">
                🇳🇵 नेपाली कभरेज
              </span>
            )}
            {isLeftBlindspot && (
              <span className="bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-md">
                <ShieldAlert size={12} /> Left Blindspot
              </span>
            )}
            {isRightBlindspot && (
              <span className="bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-md">
                <ShieldAlert size={12} /> Right Blindspot
              </span>
            )}
          </div>

          <h1 className="text-2xl sm:text-4xl font-black text-white leading-tight max-w-4xl">
            {story.ai_headline}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-xs sm:text-sm text-white/80 pt-2">
            <span className="flex items-center gap-1.5 font-bold text-blue-400 bg-blue-950/60 border border-blue-500/30 px-3 py-1 rounded-lg">
              <BookOpen size={14} /> {story.source_count} News Outlets Reporting
            </span>
            <span className="flex items-center gap-1.5">
              <Clock size={14} /> Fetched {formatTimeAgo(story.created_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Ground News Media Bias Breakdown Panel */}
      <div className="glass-card rounded-3xl p-6 sm:p-8 bg-surface border border-border shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={20} className="text-blue-400" />
            <h2 className="text-lg font-black text-foreground">Media Bias Distribution</h2>
          </div>
          <span className="text-xs text-foreground/50">
            Real-time analysis of {story.source_count} publisher perspectives
          </span>
        </div>

        {/* The 3-way Bar */}
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-black uppercase tracking-wider">
            <span className="text-blue-400">Left-leaning: {Math.round(story.bias_left_pct)}%</span>
            <span className="text-slate-400">Center: {Math.round(story.bias_center_pct)}%</span>
            <span className="text-red-400">Right-leaning: {Math.round(story.bias_right_pct)}%</span>
          </div>

          <BiasBar
            left={story.bias_left_pct}
            center={story.bias_center_pct}
            right={story.bias_right_pct}
            className="h-3.5"
          />

          {/* 3 Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="border border-blue-500/20 bg-blue-500/10 rounded-2xl p-4 text-center">
              <p className="text-3xl font-black text-blue-400">{Math.round(story.bias_left_pct)}%</p>
              <p className="text-xs font-bold text-blue-300 mt-1">Left Leaning</p>
              <p className="text-[11px] text-foreground/50 mt-0.5">
                {leftArticles.length} of {story.source_count} source{story.source_count !== 1 ? "s" : ""}
              </p>
            </div>

            <div className="border border-slate-500/20 bg-slate-500/10 rounded-2xl p-4 text-center">
              <p className="text-3xl font-black text-slate-300">{Math.round(story.bias_center_pct)}%</p>
              <p className="text-xs font-bold text-slate-200 mt-1">Center / Balanced</p>
              <p className="text-[11px] text-foreground/50 mt-0.5">
                {centerArticles.length} of {story.source_count} source{story.source_count !== 1 ? "s" : ""}
              </p>
            </div>

            <div className="border border-red-500/20 bg-red-500/10 rounded-2xl p-4 text-center">
              <p className="text-3xl font-black text-red-400">{Math.round(story.bias_right_pct)}%</p>
              <p className="text-xs font-bold text-red-300 mt-1">Right Leaning</p>
              <p className="text-[11px] text-foreground/50 mt-0.5">
                {rightArticles.length} of {story.source_count} source{story.source_count !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
        </div>

        {/* AI Clustered Summary */}
        {story.ai_summary && (
          <div className="mt-6 pt-6 border-t border-border space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-400">
              <Sparkles size={13} />
              <span>Coverage Synthesis</span>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed bg-background/60 p-4 rounded-xl border border-border">
              {story.ai_summary}
            </p>
          </div>
        )}
      </div>

      {/* Side-by-Side Perspectives Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-black text-foreground">
              Compare {story.source_count} Perspective{story.source_count !== 1 ? "s" : ""}
            </h2>
            <p className="text-xs text-foreground/60 mt-1">
              Read how different outlets framed the headline and chose their narrative.
            </p>
          </div>
        </div>

        {story.articles.length === 0 ? (
          <div className="text-center py-16 bg-surface rounded-2xl border border-border text-foreground/50">
            No articles linked to this clustered story yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {story.articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}
      </div>

      {/* Bottom return navigation */}
      <div className="pt-8 border-t border-border flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-bold text-foreground/70 hover:text-blue-400 transition-colors"
        >
          <ArrowLeft size={16} /> Back to Live Stories Feed
        </Link>
        <p className="text-xs text-foreground/40">SajhaNews Media Literacy Engine</p>
      </div>
    </div>
  );
}
