"use client";

import { useMemo, useState } from "react";
import type { ArticleDTO } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";

type PovKey = "all" | "government_critical" | "government_neutral" | "government_supportive";

const tabs: Record<PovKey, string> = {
  all: "All",
  government_critical: "Critical",
  government_neutral: "Neutral",
  government_supportive: "Supportive",
};

function povOf(a: ArticleDTO): PovKey {
  const g = a.government_framing;
  if (g === "government_critical" || g === "government_neutral" || g === "government_supportive") {
    return g;
  }
  return "government_neutral";
}

function povLabel(pov: string) {
  if (pov === "critical") return "Critical";
  if (pov === "supportive") return "Supportive";
  return "Neutral";
}

export function CoverageComparison({ articles }: { articles: ArticleDTO[] }) {
  const [selected, setSelected] = useState<PovKey>("all");

  const counts = useMemo(() => {
    let critical = 0, neutral = 0, supportive = 0;
    for (const a of articles) {
      const p = povOf(a);
      if (p === "government_critical") critical += 1;
      else if (p === "government_supportive") supportive += 1;
      else neutral += 1;
    }
    return { critical, neutral, supportive };
  }, [articles]);

  const visible =
    selected === "all" ? articles : articles.filter((a) => povOf(a) === selected);

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="font-serif text-xl font-semibold">Coverage comparison</h2>
          <p className="text-xs text-foreground/55">How each outlet frames the government</p>
        </div>
        <span className="text-xs text-foreground/50">{articles.length} outlets</span>
      </div>

      <BiasBar
        critical={counts.critical}
        neutral={counts.neutral}
        supportive={counts.supportive}
        left={0}
        center={0}
        right={0}
      />

      <div className="flex flex-wrap gap-x-4 gap-y-2 border-b border-foreground/15">
        {(Object.keys(tabs) as PovKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setSelected(key)}
            className={`border-b-2 pb-1 text-sm ${
              selected === key
                ? "border-accent font-semibold text-foreground"
                : "border-transparent text-foreground/60 hover:text-foreground"
            }`}
          >
            {tabs[key]}
          </button>
        ))}
      </div>

      <div className="divide-y divide-border border border-border bg-surface">
        {visible.length === 0 ? (
          <p className="p-4 text-sm text-foreground/55">No outlets in this division.</p>
        ) : visible.map((article) => {
          const pov = povOf(article).replace("government_", "");
          return (
            <article key={article.id} className="grid gap-2 p-4 sm:grid-cols-[8.5rem_1fr_auto] sm:items-start">
              <div className="text-xs">
                <p className="font-semibold">{article.source_name}</p>
                <p
                  className={
                    pov === "critical"
                      ? "text-accent"
                      : pov === "supportive"
                        ? "text-foreground/55"
                        : "text-foreground"
                  }
                >
                  {povLabel(pov)}
                </p>
              </div>
              <div className="min-w-0">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold underline decoration-transparent underline-offset-2 hover:decoration-foreground/40"
                >
                  {article.original_headline}
                </a>
                {article.framing_evidence && (
                  <p className="mt-1 line-clamp-2 text-xs italic text-foreground/50">
                    {article.framing_evidence}
                  </p>
                )}
              </div>
              <a
                href={article.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs uppercase tracking-wide text-foreground/55 underline decoration-foreground/25 underline-offset-2 hover:text-foreground"
              >
                Open
              </a>
            </article>
          );
        })}
      </div>
    </section>
  );
}
