"use client";

import { useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
import type { ArticleDTO } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";

type PovKey = "all" | "government_critical" | "government_neutral" | "government_supportive";

const tabs: Record<PovKey, string> = {
  all: "All",
  government_critical: "Critical of gov",
  government_neutral: "Neutral",
  government_supportive: "Supportive of gov",
};

function povOf(a: ArticleDTO): PovKey {
  const g = a.government_framing;
  if (g === "government_critical" || g === "government_neutral" || g === "government_supportive") {
    return g;
  }
  return "government_neutral";
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
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-serif text-lg font-bold">Coverage by government POV</h2>
          <p className="text-xs text-foreground/45">How each outlet frames the government</p>
        </div>
        <span className="text-xs text-foreground/45">{articles.length} outlets</span>
      </div>

      <BiasBar
        critical={counts.critical}
        neutral={counts.neutral}
        supportive={counts.supportive}
        left={0}
        center={0}
        right={0}
      />

      <div className="flex flex-wrap gap-2">
        {(Object.keys(tabs) as PovKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setSelected(key)}
            className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${
              selected === key
                ? "border-teal-800 bg-teal-800 text-white"
                : "border-border-subtle bg-white hover:bg-surface-hover"
            }`}
          >
            {tabs[key]}
          </button>
        ))}
      </div>

      <div className="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-white">
        {visible.map((article) => {
          const pov = povOf(article).replace("government_", "");
          return (
            <article key={article.id} className="grid gap-2 p-4 sm:grid-cols-[130px_1fr_auto]">
              <div className="text-xs">
                <p className="font-bold">{article.source_name}</p>
                <p
                  className={
                    pov === "critical"
                      ? "font-semibold text-red-600"
                      : pov === "supportive"
                        ? "font-semibold text-teal-700"
                        : "text-slate-500"
                  }
                >
                  {pov === "critical" ? "Critical of gov" : pov === "supportive" ? "Supportive of gov" : "Neutral"}
                </p>
              </div>
              <div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold hover:text-teal-800"
                >
                  {article.original_headline}
                </a>
                {article.framing_evidence && (
                  <p className="mt-1 text-xs italic text-foreground/45 line-clamp-2">
                    {article.framing_evidence}
                  </p>
                )}
              </div>
              <a href={article.url} target="_blank" rel="noreferrer" className="text-teal-700">
                <ExternalLink size={16} />
              </a>
            </article>
          );
        })}
      </div>
    </section>
  );
}
