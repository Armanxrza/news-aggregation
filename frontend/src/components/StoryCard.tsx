import React from 'react';
import Link from 'next/link';
import { BiasBar } from './BiasBar';
import { Clock, BookOpen, ExternalLink, ShieldAlert, Sparkles } from 'lucide-react';

const FALLBACK_THUMBNAIL =
  "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80";

export interface Story {
  id: string;
  headline: string;
  thumbnail_url: string | null;
  source_count: number;
  sources: string[];
  languages: string[];
  bias: {
    left: number;
    center: number;
    right: number;
  };
  time_ago: string;
  topic: string;
}

export function StoryCard({ story }: { story: Story }) {
  // Blindspot detection logic (Ground News signature)
  const isLeftBlindspot = story.bias.left >= 55;
  const isRightBlindspot = story.bias.right >= 55;
  const isBalanced = !isLeftBlindspot && !isRightBlindspot && Math.abs(story.bias.left - story.bias.right) < 25;

  return (
    <Link href={`/story/${story.id}`} className="group block h-full">
      <article className="glass-card rounded-2xl overflow-hidden flex flex-col h-full bg-surface border border-border transition-all duration-300 hover:shadow-2xl hover:border-blue-500/40">
        {/* Card Media Header */}
        <div className="relative h-52 w-full overflow-hidden shrink-0 bg-slate-900/60">
          <img
            src={story.thumbnail_url ?? FALLBACK_THUMBNAIL}
            alt={story.headline}
            className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105 opacity-90 group-hover:opacity-100"
            loading="lazy"
          />
          {/* Subtle vignette gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-background via-black/30 to-transparent" />

          {/* Top badges */}
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between gap-2">
            <span className="bg-background/90 backdrop-blur-md border border-border/80 px-2.5 py-1 rounded-md text-[10px] font-extrabold uppercase tracking-wider text-blue-400">
              {story.topic}
            </span>

            <div className="flex items-center gap-1.5">
              {story.languages.includes('ne') && (
                <span className="bg-red-600/90 backdrop-blur-md border border-red-400/30 px-2 py-0.5 rounded-md text-[10px] font-bold text-white flex items-center gap-1 shadow-sm">
                  🇳🇵 नेपाली
                </span>
              )}
              {isLeftBlindspot && (
                <span className="bg-blue-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 shadow-sm">
                  <ShieldAlert size={10} /> Left Blindspot
                </span>
              )}
              {isRightBlindspot && (
                <span className="bg-red-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 shadow-sm">
                  <ShieldAlert size={10} /> Right Blindspot
                </span>
              )}
            </div>
          </div>

          {/* Bottom of Image: Source count badge */}
          <div className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-background/80 backdrop-blur-md border border-border/60 text-foreground/90 text-[11px] font-bold px-2.5 py-1 rounded-lg">
            <BookOpen size={12} className="text-blue-400" />
            <span>{story.source_count} {story.source_count === 1 ? "Perspective" : "Perspectives"}</span>
          </div>
        </div>

        {/* Content Section */}
        <div className="p-5 flex flex-col flex-1 justify-between gap-4">
          <div className="space-y-3">
            <h3 className="text-base font-bold leading-snug line-clamp-2 text-foreground group-hover:text-blue-400 transition-colors">
              {story.headline}
            </h3>

            {/* Source Outlets Chips */}
            {story.sources.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {story.sources.slice(0, 3).map((src) => (
                  <span
                    key={src}
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-surface-hover text-foreground/75 border border-border"
                  >
                    {src}
                  </span>
                ))}
                {story.sources.length > 3 && (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-surface-muted text-foreground/50 border border-border">
                    +{story.sources.length - 3} more
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Ground News Bias Breakdown Footer */}
          <div className="pt-3 border-t border-border/60 space-y-2">
            <div className="flex items-center justify-between text-[11px] font-semibold">
              <span className="text-blue-400">Left {Math.round(story.bias.left)}%</span>
              <span className="text-slate-400">Center {Math.round(story.bias.center)}%</span>
              <span className="text-red-400">Right {Math.round(story.bias.right)}%</span>
            </div>

            <BiasBar
              left={story.bias.left}
              center={story.bias.center}
              right={story.bias.right}
              className="h-1.5 rounded-full"
            />

            <div className="flex items-center justify-between text-[10px] text-foreground/45 pt-1">
              <span className="flex items-center gap-1">
                <Clock size={11} /> Fetched {story.time_ago}
              </span>
              <span className="group-hover:text-blue-400 transition-colors font-medium flex items-center gap-1">
                Compare Coverage →
              </span>
            </div>
          </div>
        </div>
      </article>
    </Link>
  );
}
