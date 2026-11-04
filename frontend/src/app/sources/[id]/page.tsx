import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchSourceDetail } from "@/lib/api";
import { framingLabel, perspectiveLabel } from "@/lib/framing";
import { SourceFramingHistory } from "@/components/SourceFramingHistory";
import { formatTimeAgo } from "@/lib/utils";

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sourceId = Number(id);
  if (!Number.isInteger(sourceId)) notFound();

  let source;
  try {
    source = await fetchSourceDetail(sourceId);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-8">
      <Link href="/sources" className="text-sm text-foreground/60 hover:text-foreground">
        ← All sources
      </Link>

      <header className="space-y-5 border border-border bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-semibold">{source.name}</h1>
            <a
              href={`https://${source.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-block text-sm underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground"
            >
              {source.domain}
            </a>
          </div>
          <span className={`text-xs uppercase tracking-wide ${source.is_active ? "text-foreground" : "text-foreground/45"}`}>
            {source.is_active ? "Active" : "Inactive"}
          </span>
        </div>

        <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Language</dt>
            <dd className="mt-1 font-semibold">{source.language?.toUpperCase() ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Perspective</dt>
            <dd className="mt-1">{perspectiveLabel(source.perspective_label)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Articles crawled</dt>
            <dd className="mt-1 font-semibold tabular-nums">{source.article_count}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Last crawl</dt>
            <dd className="mt-1">
              {source.last_crawl_at ? formatTimeAgo(source.last_crawl_at) : "—"}
              {source.last_crawl_status && (
                <span className="text-foreground/50"> ({source.last_crawl_status})</span>
              )}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Framing history</dt>
            <dd className="mt-2">
              <SourceFramingHistory history={source.framing_history} />
            </dd>
          </div>
        </dl>

        {source.rss_url && (
          <p className="text-xs text-foreground/55">
            RSS{" "}
            <a href={source.rss_url} target="_blank" rel="noreferrer" className="underline decoration-foreground/30 underline-offset-2 hover:text-foreground">
              {source.rss_url}
            </a>
          </p>
        )}

        {source.ownership_notes && (
          <div className="border-t border-border pt-4 text-sm text-foreground/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-foreground/45">Ownership notes</p>
            <p className="mt-1">{source.ownership_notes}</p>
          </div>
        )}
      </header>

      <section>
        <h2 className="mb-4 font-serif text-xl font-semibold">Recent articles</h2>
        {source.recent_articles.length === 0 ? (
          <p className="text-sm text-foreground/55">No articles indexed yet.</p>
        ) : (
          <ul className="divide-y divide-border border border-border bg-surface">
            {source.recent_articles.map((a) => (
              <li key={a.id} className="p-4 hover:bg-background">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold leading-snug underline decoration-transparent underline-offset-2 hover:decoration-foreground/40"
                >
                  {a.original_headline}
                </a>
                <p className="mt-1 text-xs text-foreground/50">
                  {a.published_at ? formatTimeAgo(a.published_at) : "—"} ·{" "}
                  {framingLabel(a.government_framing)}
                </p>
                {a.snippet && <p className="mt-2 line-clamp-2 text-sm text-foreground/65">{a.snippet}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
